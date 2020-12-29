import json
import requests
import jwt
import boto3
import os
import random
import string
import logging
import re

from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# create logger
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# global variables
RANDOM_STR_LEN = 5
USER_STATUS_EXPIRY_DAYS = 0.9
PENDING_REQUEST_EXPIRY_HOURS = 0.9
TOKEN_URL = "https://api.aarogyasetu.gov.in/token"
USER_STATUS_URL = "https://api.aarogyasetu.gov.in/userstatus"
USER_STATUS_BY_REQUEST_URL = "https://api.aarogyasetu.gov.in/userstatusbyreqid"
DATE_TIME_FORMAT = "%Y-%m-%d-%H:%M:%S"
APPROVED = "Approved"
PENDING = "Pending"
WHITE = "0xFFFFFF"
MOBILE_NUMBER_EXPRESSION = re.compile(r"^\+91\d{10}$")

ssm = boto3.client("ssm")
ddb = boto3.resource("dynamodb")
secretsmanager = boto3.client("secretsmanager")


class EnvVar:
    """
    A class to store environment variables

    Attributes
    ----------
    USER_STATUS_TABLE: str
        User status table name
    REQUESTS_TABLE: str
        Pending requests table name
    API_SECRET_ARN: str
        Arn for secret stored in secrets manager
    """

    def __init__(self):
        self.USER_STATUS_TABLE = os.environ.get("USER_STATUS_TABLE")
        self.REQUESTS_TABLE = os.environ.get("REQUESTS_TABLE")
        self.API_SECRET_ARN = os.environ.get("API_SECRET_ARN")

        if not self.USER_STATUS_TABLE:
            logger.error("Must set USER_STATUS_TABLE in Lambda variables!")
            raise SystemExit
        if not self.REQUESTS_TABLE:
            logger.error("Must set REQUESTS_TABLE in Lambda variables!")
            raise SystemExit
        if not self.API_SECRET_ARN:
            logger.error("Must set API_SECRET_ARN in Lambda variables!")
            raise SystemExit


class Secret:
    """
    A class to store Aarogya Setu API credentials

    Attributes
    ----------
    JWT_SECRET: jwt secret set in Aarogya Setu dashboard
    API_KEY: api key given by Aarogya Setu
    PASSWORD: password for Aarogya Setu account
    USERNAME: username for Aarogya Setu account
    """

    def __init__(self, envvar):
        """
        Get credentials from secrets manager store

        Parameters
        ----------
        envvar: EnvVar
            object contains environment variables
        """

        response = {}
        try:
            response = secretsmanager.get_secret_value(SecretId=envvar.API_SECRET_ARN)
        except ClientError as e:
            logger.error(f"Failed to get secrets from secrets manager.\n{e}")

        secrets = {}
        if "SecretString" in response:
            secrets = json.loads(response["SecretString"])

        self.JWT_SECRET = secrets.get("JWT_SECRET")
        self.API_KEY = secrets.get("API_KEY")
        self.PASSWORD = secrets.get("PASSWORD")
        self.USERNAME = secrets.get("USERNAME")

        if not self.JWT_SECRET:
            logger.error("Could not get JWT_SECRET from secrets manager")
            raise SystemExit
        if not self.API_KEY:
            logger.error("Could not get API_KEY from secrets manager")
            raise SystemExit
        if not self.PASSWORD:
            logger.error("Could not get PASSWORD from secrets manager")
            raise SystemExit
        if not self.USERNAME:
            logger.error("Could not get USERNAME from secrets manager")
            raise SystemExit


def expired(expdate):
    """
    Checks if the expiry date field from a record is past

    Parameters
    ----------
    expdata: str
        Expiry date timestamp
    """

    return expdate < str(int(datetime.now().timestamp()))


def create_return_header():
    """Create a return header with appropriate options"""

    headers = {
        "Access-Control-Allow-Headers": "Authorization",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Credentials": True,
    }

    return headers


def create_return_body(mobile_number, message, colour="#FFFFFF"):
    """
    Create jsonified return response body

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    message: str
        User status message
    color: str
        User status colour hex code
    """

    body = {"mobile_number": mobile_number, "message": message, "colour": colour}

    return json.dumps(body)


def create_return_response(status_code, body):
    """
    Create return status using a fixed set of header options and the
    status_code and body passed as parameters.

    Parameters
    ----------
    status_code: int
        HTTP status code of return response
    body: str
        Body of return response
    """

    headers = {
        "Access-Control-Allow-Headers": "Authorization",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Credentials": True,
    }

    return {"headers": headers, "statusCode": status_code, "body": body}


def create_request_header(secret, token=None):
    """
    Create header for API request to Aarogya Setu. There can be two types
    of headers one with token and one without it.

    Parameters
    ----------
    envvar: Secret
        object contains api secrets
    token: str
        Request token given returned as reponse from TOKEN_URL
    """

    if token is None:
        return {
            "accept": "application/json",
            "x-api-key": secret.API_KEY,
            "Content-Type": "application/json",
        }
    else:
        return {
            "accept": "application/json",
            "x-api-key": secret.API_KEY,
            "Content-Type": "application/json",
            "Authorization": token,
        }


def create_trace_id():
    """
    Create a unique trace_id by combining current timestamp and some random
    ascii uppercase text.
    """

    timestamp = datetime.today().strftime(DATE_TIME_FORMAT)
    randomstr = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=RANDOM_STR_LEN)
    )
    trace_id = timestamp + "-" + randomstr

    return trace_id


def store_user_status(number, status, request_status, envvar):
    """
    Takes a status response adds an expiration time stamp to it and
    stores it in user status table.

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    status: dict
        Status returned by Aarogya Setu API
    request_status: str
        Request status is either Approved or Rejected
    envvar: EnvVar
        Object contains environment variables
    """

    expdate = datetime.now() + timedelta(days=USER_STATUS_EXPIRY_DAYS)
    expdate = str(int(expdate.timestamp()))
    user_status_table = ddb.Table(envvar.USER_STATUS_TABLE)

    try:
        user_status_table.put_item(
            Item={
                "mobile_number": number,
                "message": status["message"],
                "colour": status["color_code"],
                "expdate": expdate,
                "request_status": request_status,
            },
        )
    except ClientError as e:
        logger.error(f"Failed to store user status\n{e}")


def store_pending_request(number, token, request_id, envvar):
    """
    Store pending request identified by the tuple of mobile number, API token,
    and unique request id. The record has an expiry duration.

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    token: str
        Request token given returned as reponse from TOKEN_URL
    request_id: str
        Request id returned by response from USER_STATUS_URL
    envvar: EnvVar
        Object contains environment variables
    """

    expdate = datetime.now() + timedelta(hours=PENDING_REQUEST_EXPIRY_HOURS)
    expdate = str(int(expdate.timestamp()))
    requests_table = ddb.Table(envvar.REQUESTS_TABLE)

    try:
        requests_table.put_item(
            Item={
                "mobile_number": number,
                "token": token,
                "request_id": request_id,
                "expdate": expdate,
            },
        )
    except ClientError as e:
        logger.error(f"Failed to store pending request.\n{e}")


def delete_pending_request(number, envvar):
    """
    Delete pending request after it has been used to successfully get user
    status.

    Note: If a request_id has been used to successfully get user status it
    should be deleted because it cannot be used to make status requests
    anymore.

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    envvar: EnvVar
        Object contains environment variables
    """

    requests_table = ddb.Table(envvar.REQUESTS_TABLE)

    try:
        requests_table.delete_item(Key={"mobile_number": number})
    except ClientError as e:
        logger.error(f"Failed to delete pending request.\n{e}")


def get_pending_request(number, envvar):
    """
    Get pending request from table. If it has expired return None

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    envvar: EnvVar
        Object contains environment variables
    """

    requests_table = ddb.Table(envvar.REQUESTS_TABLE)

    try:
        item = requests_table.get_item(Key={"mobile_number": number}).get("Item")
    except ClientError as e:
        logger.error(f"Failed to get pending request from table.\n{e}")
        return None

    if item and not expired(item["expdate"]):
        return item
    else:
        return None


def check_user_status(number, envvar):
    """
    Get user status from table. If it has expired return None

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    envvar: EnvVar
        Object contains environment variables
    """

    user_status_table = ddb.Table(envvar.USER_STATUS_TABLE)

    try:
        item = user_status_table.get_item(Key={"mobile_number": number}).get("Item")
    except ClientError as e:
        logger.error(f"Failed to get existing user status.\n{e}")
        return None

    if item and not expired(item["expdate"]):
        return item
    else:
        return None


def get_token(secret):
    """
    Get API token from Aarogya Setu it is valid for one hour and one succesful
    status request

    Parameters
    ----------
    envvar: Secret
        Object contains secrets
    """

    url = TOKEN_URL
    headers = create_request_header(secret)
    body = {"username": secret.USERNAME, "password": secret.PASSWORD}

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        logger.error(f"Aarogya Setu API failed to get token.\n{res.content}")
        return None
    else:
        return res.json()["token"]


def create_new_request(number, token, secret):
    """
    Create a new request with Aarogya Setu. Store both token and request id
    in the pending requests table.

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    token: str
        Request token given returned as reponse from TOKEN_URL
    secret: Secret
        Object contains secrets
    """

    url = USER_STATUS_URL
    trace_id = create_trace_id()

    headers = create_request_header(secret, token)
    body = {
        "phone_number": number,
        "trace_id": trace_id,
        "reason": "Office entry",
    }

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        logger.error(f"Aarogya Setu API failed to get request id.\n{res.content}")
        return None
    else:
        return res.json()["requestId"]


def get_status_content(number, token, request_id, secret):
    """
    Get status for a pending request. Delete entry from pending request table
    if successfully gets status

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    token: str
        Request token given returned as reponse from TOKEN_URL
    secret: Secret
        Object contains secrets
    """

    url = USER_STATUS_BY_REQUEST_URL
    headers = create_request_header(secret, token)
    body = {"requestId": request_id}

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        logger.error(
            f"Aarogya Setu API failed to get status for given request.\n{res.content}"
        )
        return None
    else:
        return res.json()


def decode_status(content, secret):
    """
    Decode user status using the jwt secret token and return an appropriate
    return status

    Parameters
    ----------
    content: dict
        Encoded status returned as reponse from USER_STATUS_BY_REQUEST_URL
    secret: Secret
        Object contains secrets
    """

    coded_status = content["as_status"]
    status = jwt.decode(coded_status, secret.JWT_SECRET)
    logger.info(status)

    return status["as_status"]


def create_reponse_from_status(number, status, request_status):
    """
    Create return response based on request status

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    status: dict
        status of user given by Aarogya Setu API
    request_status: str
        Request status between Approved, Pending and Rejected
    """

    if request_status == APPROVED:
        message = create_return_body(number, status["message"], status["color_code"])
        return_response = create_return_response(200, message)
    elif request_status == PENDING:
        message = create_return_body(number, "Please wait for user to approve request")
        return_response = create_return_response(200, message)
    else:
        message = create_return_body(
            number, "User has denied request. Please make a new request"
        )
        return_response = create_return_response(200, message)

    return return_response


def valid_mobile_number(number):
    """
    Check if the mobile number is valid

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    """

    return MOBILE_NUMBER_EXPRESSION.match(number)


def check_mobile_number(number):
    """
    Check mobile number for COVID status. It first checks user status table
    for cached entry. If the entry is expired it makes a fresh request and then
    gets status for the request

    Parameters
    ----------
    number: str
        User mobile number of the format "+91XXXXXXXXXX"
    """

    # reject empty or invalid mobile numbers
    if not (number and valid_mobile_number(number)):
        message = create_return_body(number, "Mobile number is invalid")
        return create_return_response(200, message)

    envvar = EnvVar()
    secret = Secret(envvar)

    # check if status exists in ddb
    entry = check_user_status(number, envvar)

    # returned cached entry if it exists and status is not pending or denied
    if entry is not None and entry["request_status"] == APPROVED:
        message = create_return_body(number, entry["message"], entry["colour"])
        return create_return_response(200, message)

    # check ddb for pending request
    entry = get_pending_request(number, envvar)

    # create new request if it doesn't exist
    if entry is None:
        token = get_token(secret)

        if token is None:
            message = create_return_body(
                number, "Failed to get token from Aarogya Setu. Please try again"
            )
            return create_return_response(502, message)

        request_id = create_new_request(number, token, secret)

        if request_id is None:
            message = create_return_body(
                number, "Failed to get request id from Aarogya Setu. Please try again"
            )
            return create_return_response(502, message)

        store_pending_request(number, token, request_id, envvar)
    else:
        token = entry["token"]
        request_id = entry["request_id"]

    content = get_status_content(number, token, request_id, secret)

    if content is None:
        message = create_return_body(
            number, "Failed to get status from Aarogya Setu. Please try again"
        )
        return create_return_response(502, message)

    # default status
    status = {
        "message": "User as rejected request. Please create a new request",
        "color_code": WHITE,
    }

    # store rejected and approved statuses
    if content["request_status"] != PENDING:

        if content["request_status"] == APPROVED:
            status = decode_status(content, secret)

        store_user_status(number, status, content["request_status"], envvar)
        delete_pending_request(number, envvar)

    return_response = create_reponse_from_status(
        number, status, content["request_status"]
    )
    logger.info(return_response)

    return return_response
