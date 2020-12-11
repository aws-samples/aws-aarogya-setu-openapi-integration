import zipfile
import os

from pip._internal import main as pip_main


def create_dependency_layer():
    """
    Installs dependencies in a target directory and then
    packages it into a zip file that can be used by CDK
    to create Lambda dependency layer
    """

    # change directory so that relative paths work
    os.chdir("lambda")

    # install dependencies
    requirements_file_path = "requirements.txt"
    target_directory = "python"
    pip_main(
        [
            "install",
            "-r",
            requirements_file_path,
            "--target",
            target_directory,
        ]
    )

    # package dependencies as a zip file
    zip_file_path = "dependency-layer.zip"
    dep_zip = zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(target_directory):
        for file in files:
            dep_zip.write(os.path.join(root, file))

    dep_zip.close()


if __name__ == "__main__":
    create_dependency_layer()
