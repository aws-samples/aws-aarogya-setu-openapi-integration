import os
import logging
import boto3

from botocore.exceptions import ClientError
from get_status import check_mobile_number

sqs = boto3.resource("sqs")
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Receive single message from queue and check status with Aarogya Setu.
    Delete message after checking status

    Parameters
    ----------
    event: dict
        event parameters passed to function
    context: dict
        context parameters passed to function
    """

    # queue event sent sends only one number at a time
    mobile_number = None
    message = event["Records"][0]
    if message:
        mobile_number = message.get("body")

    return_status = check_mobile_number(mobile_number)
    logger.info(return_status)

    # delete request from queue
    queue = sqs.Queue(os.environ["QUEUE_URL"])
    try:
        queue.delete_messages(
            Entries=[{"Id": "1", "ReceiptHandle": message["receiptHandle"]}]
        )
    except ClientError as e:
        logger.error(f"Failed to delete message {message}.\n{e}")
