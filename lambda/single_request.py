import json
import logging

from get_status import check_mobile_number

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Receive a mobile number and query Aarogya Setu about it's status.
    Mobile number format is "+9198XXXXXXXX"

    Parameters
    ----------
    event: dict
        event parameters passed to function
    context: dict
        context parameters passed to function
    """

    mobile_number = None
    body = event.get("body")
    if body:
        mobile_number = json.loads(body).get("mobile_number")

    return_status = check_mobile_number(mobile_number)
    logger.info(return_status)

    return return_status
