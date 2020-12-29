import os
import json
import boto3
import logging

from botocore.exceptions import ClientError
from datetime import datetime


USER_STATUS_EXPIRY_DAYS = 0.9

ddb = boto3.resource("dynamodb")
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
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Credentials": True,
    }

    return headers


def create_response(status_code, body):
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
    Scans user status table and returns payload of upto 1 MB in size

    Parameters
    ----------
    event: dict
        event parameters passed to function
    context: dict
        context parameters passed to function
    """

    USER_STATUS_TABLE = os.environ.get("USER_STATUS_TABLE")
    table = ddb.Table(USER_STATUS_TABLE)

    try:
        data = table.scan()  # returns a payload of max 1 MB
    except ClientError as e:
        logger.error(f"Unable to scan table {USER_STATUS_TABLE}.\n{e}")
        return create_response(502, json.dumps([]))

    items = []
    for item in data["Items"]:

        # ignore expired items
        if item["expdate"] < str(int(datetime.now().timestamp())):
            continue

        del item["expdate"]
        del item["request_status"]

        item["colour"] = "#FFFFFF"  # temporary
        items.append(item)

    return create_response(200, json.dumps(items))
