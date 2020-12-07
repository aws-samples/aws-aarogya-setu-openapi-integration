import boto3
import re

from os import path


def generate_exports():
    """
    Generate aws-exports.js file by fetching output values
    from deployed cloudformation stack. Replace placeholders
    with these values in aws-exports-template.js
    """

    cfn = boto3.resource("cloudformation")
    stack = cfn.Stack("asetuapi")
    template_values = {}
    for output in stack.outputs:
        if "ExportName" in output:
            template_values[output["ExportName"]] = output["OutputValue"]

    template = ""
    with open(path.join("client", "aws-exports-template.js")) as f:
        template = f.read()

    for key, value in template_values.items():
        print(f"Writing {key} with {value}")
        template = template.replace(key, value)

    with open(path.join("client", "test.js"), "w") as f:
        f.write(template)


if __name__ == "__main__":
    generate_exports()
