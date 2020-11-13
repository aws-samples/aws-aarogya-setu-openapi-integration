import json
import boto3
import os
import logging

from botocore.exceptions import ClientError

sqs = boto3.resource("sqs")
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_response_headers():
    """
    Create response headers
    """

    headers = {
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Credentials": True,
    }

    return headers


def create_return_status(status_code, body):
    """
    Create return status

    Parameters
    ----------
    status_code: int
        Status code for response
    body: str
        response body
    """

    return {
        "headers": create_response_headers(),
        "statusCode": status_code,
        "body": body,
    }


def handler(event, context):
    """
    Receive comma separated mobile numbers and push them into a queue.
    Format is "+9198XXXXXXXX,+9197XXXXXXXX"

    Parameters
    ----------
    event: dict
        event parameters passed to function
    context: dict
        context parameters passed to function
    """

    queue = sqs.Queue(os.environ["QUEUE_URL"])
    numbers = json.loads(event["body"])["numbers"]
    failed = []

    # upload numbers to queue one at a time
    for number in numbers.split(","):
        try:
            queue.send_message(MessageBody=number)
        except ClientError as e:
            logger.error(f"Failed to add {number} to queue.\n{e}")
            failed.append(number)
        else:
            logger.info(f"Added to queue {number}")

    if failed:
        failed_numbers = ",".join(failed)
        body = json.dumps(f"Failed to add upload numbers: {failed_numbers}")
    else:
        body = json.dumps("Succesfully uploaded all numbers")

    return_status = create_return_status(200, body)
    logger.info(return_status)
    return return_status
