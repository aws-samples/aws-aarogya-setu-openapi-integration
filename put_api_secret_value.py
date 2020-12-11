import boto3
import json

from botocore.exceptions import ClientError


def put_api_secret_value():
    """
    Fetch full secret arn from cloudformation output values. Update
    secret with values from secret.json
    """

    # get full secret arn from cloudformation
    cfn = boto3.resource("cloudformation")
    stack = cfn.Stack("asetuapi")
    secret_arn = None
    for output in stack.outputs:
        if output.get("ExportName") == "API-SECRET-ARN":
            secret_arn = output["OutputValue"]

    # put values in secret
    secretsmanager = boto3.client("secretsmanager")
    api_secrets = None
    with open("secrets.json") as f:
        api_secrets = json.loads(f.read())

    try:
        response = secretsmanager.put_secret_value(
            SecretId=secret_arn, SecretString=json.dumps(api_secrets)
        )
        print(f"Successfully updated secret.\n{response}")
    except ClientError as e:
        print(f"Unable to put secret value.\n{e}")


if __name__ == "__main__":
    put_api_secret_value()
