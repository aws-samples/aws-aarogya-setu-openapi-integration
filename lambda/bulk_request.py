import json
import boto3
import os
import logging

from logging import getLogger


sqs = boto3.resource("sqs")
LOG = getLogger()
LOG.setLevel(logging.INFO)


def create_response_headers():

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
    """"

    return {"headers": create_response_headers(), "statusCode": status_code, "body": body}


def handler(event, context):
    """
    Receive comma separated mobile numbers and push them into a queue.
    Format is "+9198XXXXXXXX,+9197XXXXXXXX"
    """

    queue = sqs.Queue(os.environ["QUEUE_URL"])
    numbers = json.loads(event["body"])["numbers"]

    for number in numbers.split(","):
        queue.send_message(MessageBody=number)
        LOG.info(f"Added to queue {number}")

    headers = {
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Credentials": True,
    }

    return_status = {}
    return_status["headers"] = headers
    return_status["statusCode"] = 200
    return_status["body"] = json.dumps("Successfully uploaded all numbers")
    return return_status
