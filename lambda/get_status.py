import json
import requests
import jwt
import boto3
import os
import random
import string
import logging

from datetime import datetime, timedelta

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
ssm = boto3.client("ssm")
ddb = boto3.resource("dynamodb")


class EnvVar:
    """
    A class to store environemnt variables

    Attributes
    ----------
    JWT_KEY: str
        Parameter key to get jwt secret for Aarogya Setu API
    API_KEY_KEY: str
        Parameter key to get api key Aarogya Setu API
    USERNAME_KEY: str
        Parameter key to get username for Aarogya Setu API
    PASSWORD_KEY: str
        Parameter key to get password for Aarogya Set API
    USER_STATUS_TABLE: str
        User status table name
    REQUESTS_TABLE: str
        Pending requests table name
    """

    JWT_KEY = os.environ.get("JWT_KEY")
    API_KEY_KEY = os.environ.get("API_KEY_KEY")
    USERNAME_KEY = os.environ.get("USERNAME_KEY")
    PASSWORD_KEY = os.environ.get("PASSWORD_KEY")
    USER_STATUS_TABLE = os.environ.get("USER_STATUS_TABLE")
    REQUESTS_TABLE = os.environ.get("REQUESTS_TABLE")

    def __init__(self):
        if not self.JWT_KEY:
            logger.error("Must set JWT_KEY in Lambda variables!")
            raise SystemExit
        if not self.API_KEY_KEY:
            logger.error("Must set API_KEY_KEY in Lambda variables!")
            raise SystemExit
        if not self.USERNAME_KEY:
            logger.error("Must set USERNAME_KEY in Lambda variables!")
            raise SystemExit
        if not self.PASSWORD_KEY:
            logger.error("Must set PASSWORD_KEY in Lambda variables!")
            raise SystemExit
        if not self.USER_STATUS_TABLE:
            logger.error("Must set USER_STATUS_TABLE in Lambda variables!")
            raise SystemExit
        if not self.REQUESTS_TABLE:
            logger.error("Must set REQUESTS_TABLE in Lambda variables!")
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

    TODO: decrypt tokens
    """

    def __init__(self, envvar):
        """
        Get credentials from parameter store

        Parameters
        ----------
        envvars: EnvVar
            object contains environment variables
        """

        responses = ssm.get_parameters(
            Names=[envvar.JWT_KEY, envvar.API_KEY_KEY, envvar.USERNAME_KEY, envvar.PASSWORD_KEY],
            WithDecryption=False,
        )

        parameters = {}
        for response in responses.get("Parameters"):
            parameters[response.get("Name")] = response.get("Value")

        self.JWT_SECRET = parameters.get(envvar.JWT_KEY)
        self.API_KEY = parameters.get(envvar.API_KEY_KEY)
        self.PASSWORD = parameters.get(envvar.PASSWORD_KEY)
        self.USERNAME = parameters.get(envvar.USERNAME_KEY)

        if not self.JWT_SECRET:
            logger.error("Could not get JWT_SECRET from parameter store")
            raise SystemExit
        if not self.API_KEY:
            logger.error("Could not get API_KEY from parameter store")
            raise SystemExit
        if not self.PASSWORD:
            logger.error("Could not get PASSWORD from parameter store")
            raise SystemExit
        if not self.USERNAME:
            logger.error("Could not get USERNAME from parameter store")
            raise SystemExit


def create_return_header():
    """Create a return header with appropriate options"""

    headers = {
        "Access-Control-Allow-Headers": "Authorization",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Credentials": True,
    }

    return headers


def create_return_status(status_code, body):
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

    return {"headers": headers, "statusCode": statusCode, "body": body}


def create_request_header(secret, token = None):
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



def store_user_status(number, return_status, envvar):
    """
    Takes a status response adds an expiration time stamp to it and
    stores it in user status table.

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    return_status: dict
        Return response to be returned by API
    envvar: EnvVar
        Object contains environment variables

    TODO: Error handling if network fails
    """

    expdate = datetime.now() + timedelta(days=USER_STATUS_EXPIRY_DAYS)
    expdate = str(int(expdate.timestamp()))
    user_status_table = ddb.Table(envvar.USER_STATUS_TABLE)

    user_status_table.put_item(
        Item={
            "mobile_number": number,
            "message": return_status["body"],
            "expdate": expdate,
            "statusCode": return_status["statusCode"],
        },
    )


def store_pending_request(number, token, request_id):
    """
    Store pending request identified by the tuple of mobile number, API token,
    and unique request id. The record has an expiry duration.

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    token: str
        Request token given returned as reponse from TOKEN_URL
    request_id: str
        Request id returned by response from USER_STATUS_URL
    envvar: EnvVar
        Object contains environment variables

    TODO: Add error handling
    """

    expdate = datetime.now() + timedelta(hours=PENDING_REQUEST_EXPIRY_HOURS)
    expdate = str(int(expdate.timestamp()))
    requests_table = ddb.Table(envvar.REQUESTS_TABLE)

    requests_table.put_item(
        Item={
            "mobile_number": number,
            "token": token,
            "request_id": request_id,
            "expdate": expdate,
        },
    )


def delete_pending_request(number):
    """
    Delete pending request after it has been used to successfully get user
    status

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    envvar: EnvVar
        Object contains environment variables
    """

    requests_table = ddb.Table(envvar.REQUESTS_TABLE)
    requests_table.delete_item(Key={"mobile_number": number})


def get_pending_request(number):
    """
    Get pending request from table. If it has expired return None

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    envvar: EnvVar
        Object contains environment variables

    TODO: check expiry and return none
    """

    requests_table = ddb.Table(envvar.REQUESTS_TABLE)
    return requests_table.get_item(Key={"mobile_number": number}).get("Item")


def check_user_status(number):
    """
    Get user status from table. If it has expired return None

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    envvar: EnvVar
        Object contains environment variables

    TODO: check expiry and return none
    """

    user_status_table = ddb.Table(envvar.USER_STATUS_TABLE)
    return user_status_table.get_item(Key={"mobile_number": number}).get("Item")


def get_token(secret):
    """
    Get API token from Aarogya Setu it is valid for one hour and one succesful
    status request

    Parameters
    ----------
    envvar: Secret
        Object contains secrets

    TODO: fix error message
    """

    url = TOKEN_URL
    headers = create_request_header(secret.API_KEY)
    body = {"username": secret.USERNAME, "password": secret.PASSWORD}

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        return None
    else:
        return res.json()["token"]

        return_status = None
        print(res.content)
        error = json.loads(res.content)["error_message"]
        return_status["statusCode"] = 203
        return_status["body"] = json.dumps(
            "Aarogya Set API failed to get token. Please try again. Error: " + error
        )
        return return_status


def create_new_request(number, token, secret):
    """
    Create a new request with Aarogya Setu. Store both token and request id
    in the pending requests table.

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    token: str
        Request token given returned as reponse from TOKEN_URL
    secret: Secret
        Object contains secrets

    TODO: return error message
    """

    # get request id
    url = USER_STATUS_URL
    trace_id = create_trace_id()

    headers = create_request_header(secret.API_KEY, token)
    body = {
        "phone_number": number,
        "trace_id": trace_id,
        "reason": "Office entry",
    }

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        # TODO log error
        # error = json.loads(res.content)["error_message"]
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
        User mobile number of the format "+919XXXXXXXXX"
    token: str
        Request token given returned as reponse from TOKEN_URL
    secret: Secret
        Object contains secrets
    """

    url = USER_STATUS_BY_REQUEST_URL
    headers = create_request_header(secret.API_KEY, token)
    body = {"requestId": request_id}

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        # TODO log error
        # error = json.loads(res.content)["error_message"]
        return None

    return res.json()


def decode_status(number, content, secret):
    """
    Decode user status using the jwt secret token and return an appropriate
    return status

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    content: dict
        Encoded status returned as reponse from USER_STATUS_BY_REQUEST_URL
    secret: Secret
        Object contains secrets
    """

    if content["request_status"] == "Approved":
        coded_status = content["as_status"]
        status = jwt.decode(coded_status, secret.JWT_SECRET)

        message = json.dumps(status["as_status"]["message"])
        return_status = create_return_status(200, message)

        # delete entry because token and request have expired

    elif content["request_status"] == "Pending":
        message = json.dumps("Please wait for user to approve request")
        return_status = create_return_status(200, message)

    else:
        message = json.dumps("User has denied request. Please make a new request")
        return_status = create_return_status(200, message)

    return return_status


def check_mobile_number(number):
    """
    Check mobile number for COVID status. It first checks user status table
    for cached entry. If the entry is expired it makes a fresh request and then
    gets status for the request

    Parameters
    ----------
    number: str
        User mobile number of the format "+919XXXXXXXXX"
    """

    envvar = EnvVar()
    secret = Secret(envvar)

    # check if status exists in ddb
    entry = check_user_status(number)

    # returned cached entry if it exists and status is not pending or denied
    if entry is not None and entry["statusCode"] == 200:
        return create_return_status(200, entry["message"])

    # check ddb for pending request
    entry = get_pending_request(number)

    # create new request if it doesn't exist
    if entry is None:
        token = get_token(secret)

        if token is None:
            message = json.dumps(
                "Failed to get token from Aarogya Setu. Please try again"
            )
            return create_return_status(200, message)

        request_id = create_new_request(number, token, secret)

        if request_id is None:
            message = json.dumps(
                "Failed to get request id from Aarogya Setu. Please try again"
            )
            return create_return_status(200, message)

        store_pending_request(number, token, request_id)
    else:
        token = entry["token"]
        request_id = entry["request_id"]

    content = get_status_content(number, token, request_id, secret)
    return_status = decode_status(number, content, secret)

    store_user_status(number, return_status)

    return return_status
