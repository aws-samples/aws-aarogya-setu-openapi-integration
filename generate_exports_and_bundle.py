import boto3
import os

from botocore.exceptions import ClientError


def get_stack_outputs():
    """
    Gets asetuapi stack outputs if it exists
    """

    cfn = boto3.client("cloudformation")

    try:
        asetuapi_stack = cfn.describe_stacks(StackName="asetuapi")
    except ClientError:
        print(
            "The frontend application will be bundled once asetuapi stack is deployed"
        )
        return None
    else:
        return asetuapi_stack[0]["Outputs"]


def generate_exports_and_bundle():
    """
    Generate aws-exports.js file by fetching output values
    from deployed cloudformation stack. Replace placeholders
    with these values in aws-exports-template.js

    Next it builds and exports the application as static files
    into the out directory so that it can be deployed to s3
    """

    # file paths
    template_path = "aws-exports-template.js"
    export_file_path = "aws-exports.js"
    out_path = "out"

    # change directory so that relative paths work
    cwd = os.getcwd()
    os.chdir("client")

    # create directory if it doesn't exist
    if not os.path.isdir(out_path):
        os.mkdir("out")

    stack_outputs = get_stack_outputs

    # create new export file only if it doesn't exist and backend stack is deployed
    if not os.path.isfile(export_file_path) and stack_outputs:

        template_values = {}
        for output in stack_outputs:
            if "ExportName" in output:
                template_values[output["ExportName"]] = output["OutputValue"]

        # replace placeholders in templates and write to file
        template = ""
        with open(template_path) as f:
            template = f.read()

        for key, value in template_values.items():
            print(f"Writing {key} with {value}")
            template = template.replace(key, value)

        with open(export_file_path, "w") as f:
            f.write(template)

    # build and export app static files if exports.js exists
    if os.path.isfile(export_file_path):
        os.system("npm install && npm run build")

    # change working directory back
    os.chdir(cwd)


if __name__ == "__main__":
    generate_exports_and_bundle()
