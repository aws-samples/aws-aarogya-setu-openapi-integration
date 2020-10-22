import json
import boto3
import os
import logging

from logging import getLogger


# global variables
sqs = boto3.resource("sqs")
queue = sqs.Queue(os.environ["QUEUE_URL"])
LOG = getLogger()
LOG.setLevel(logging.INFO)


def handler(event, _):
    """
    Receive comma separated mobile numbers and push them into a queue.
    Format is "+9198XXXXXXXX,+9197XXXXXXXX"
    """

    numbers = json.loads(event["body"])["numbers"]

    for number in numbers.split(","):
        queue.send_message(MessageBody=number)
        LOG.info(f"Added to queue {number}")

    headers = {
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        "Access-Control-Allow-Credentials": True,
    }

    return_status = {}
    return_status["headers"] = headers
    return_status["statusCode"] = 200
    return_status["body"] = json.dumps("Successfully uploaded all numbers")
    return return_status
