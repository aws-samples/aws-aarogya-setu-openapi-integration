import os
import logging
import boto3

from get_status import check_mobile_number

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
sqs = boto3.resource("sqs")
queue = sqs.Queue(os.environ["QUEUE_URL"])


def handler(event, context):
    """
    Receive single message from queue and check status with Aarogya Setu.
    Delete message after checking status
    """

    message = event["Records"][0]
    mobile_number = message["body"]
    LOG.info(mobile_number)

    # ignore return status
    return_status = check_mobile_number(mobile_number)
    LOG.info(return_status)

    # delete request from queue
    response = queue.delete_messages(
        Entries=[{"Id": "1", "ReceiptHandle": message["receiptHandle"]}]
    )
    LOG.info(response)
