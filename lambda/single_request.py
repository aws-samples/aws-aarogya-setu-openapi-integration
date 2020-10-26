import json
import logging

from get_status import check_mobile_number

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)


def handler(event, context):
    """
    Receive a mobile number and query Aarogya Setu about it's status.
    Mobile number format is "+9198XXXXXXXX"
    """

    mobile_number = json.loads(event["body"])["mobile_number"]
    return_status = check_mobile_number(mobile_number)
    LOG.info(return_status)

    return return_status
