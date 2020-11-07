import json
import requests
import jwt
import boto3
import os
import random
import string
import logging

from datetime import datetime, timedelta

# global variables
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
RANDOM_STR_LEN = 5
USER_STATUS_EXPIRY_DAYS = 0.9
PENDING_REQUEST_EXPIRY_HOURS = 0.9
TOKEN_URL = "https://api.aarogyasetu.gov.in/token"
USER_STATUS_URL = "https://api.aarogyasetu.gov.in/userstatus"
USER_STATUS_BY_REQUEST_URL = "https://api.aarogyasetu.gov.in/userstatusbyreqid"
DATE_TIME_FORMAT = "%Y-%m-%d-%H:%M:%S"
ssm = boto3.client("ssm")
ddb = boto3.resource("dynamodb")


def create_return_header():
    """Create a return header with appropriate options"""

    headers = {
        "Access-Control-Allow-Headers": "Authorization",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Credentials": True,
    }

    return headers


def create_return_status(status_code: int, body: str):
    """ 
    Create return status using a fixed set of header options and the
    status_code and body passed as parameters.

    Parameters
    ----------
    status_code: HTTP status code of return response
    body: Body of return response
    """

    headers = {
        "Access-Control-Allow-Headers": "Authorization",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Credentials": True,
    }

    return {"headers": headers, "statusCode": statusCode, "body": body}


def create_request_header(API_KEY: str, token: str = None):
    """
    Create header for API request to Aarogya Setu. There can be two types
    of headers one with token and one without it.

    Parameters
    ----------
    API_KEY: API_KEY given by aarogya setu fetched from parameter store
    token: Request token given returned as reponse from TOKEN_URL
    """

    if token is None:
        return {
            "accept": "application/json",
            "x-api-key": API_KEY,
            "Content-Type": "application/json",
        }
    else:
        return {
            "accept": "application/json",
            "x-api-key": API_KEY,
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


def fetch_parameters():
    """
    Fetch Aarogya Setu API specific credentials and keys from parameter store

    TODO: decrypt tokens
    TODO: return none if network error
    """

    JWT_KEY = os.environ.get("JWT_KEY")
    API_KEY_KEY = os.environ.get("API_KEY_KEY")
    USERNAME_KEY = os.environ.get("USERNAME_KEY")
    PASSWORD_KEY = os.environ.get("PASSWORD_KEY")

    responses = ssm.get_parameters(
        Names=[JWT_KEY, API_KEY_KEY, USERNAME_KEY, PASSWORD_KEY],
        WithDecryption=False,
    )

    parameters = {}
    for response in responses["Parameters"]:
        parameters[response["Name"]] = response["Value"]

    JWT_SECRET = parameters[JWT_KEY]
    API_KEY = parameters[API_KEY_KEY]
    PASSWORD = parameters[PASSWORD_KEY]
    USERNAME = parameters[USERNAME_KEY]

    return JWT_SECRET, API_KEY, PASSWORD, USERNAME


def store_user_status(number, return_status):
    """
    Takes a status response adds an expiration time stamp to it and
    stores it in user status table.

    Parameters
    ----------
    number: User mobile number of the format "+919XXXXXXXXX"
    return_status: Return response to be returned by API

    TODO: Error handling if network fails
    """

    expdate = datetime.now() + timedelta(days=USER_STATUS_EXPIRY_DAYS)
    expdate = str(int(expdate.timestamp()))
    user_status_table = ddb.Table(os.environ["USER_STATUS_TABLE"])

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
    number: User mobile number of the format "+919XXXXXXXXX"
    token: Request token given returned as reponse from TOKEN_URL
    request_id: Request id returned by response from USER_STATUS_URL

    TODO: Add error handling
    """

    expdate = datetime.now() + timedelta(hours=PENDING_REQUEST_EXPIRY_HOURS)
    expdate = str(int(expdate.timestamp()))
    requests_table = ddb.Table(os.environ["REQUESTS_TABLE"])

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
    number: User mobile number of the format "+919XXXXXXXXX"
    """

    requests_table = ddb.Table(os.environ["REQUESTS_TABLE"])
    requests_table.delete_item(Key={"mobile_number": number})


def get_pending_request(number):
    """
    Get pending request from table. If it has expired return None

    Parameters
    ----------
    number: User mobile number of the format "+919XXXXXXXXX"

    TODO: check expiry and return none
    """

    requests_table = ddb.Table(os.environ["REQUESTS_TABLE"])
    return requests_table.get_item(Key={"mobile_number": number}).get("Item")


def check_user_status(number):
    """
    Get user status from table. If it has expired return None

    Parameters
    ----------
    number: User mobile number of the format "+919XXXXXXXXX"

    TODO: check expiry and return none
    """

    user_status_table = ddb.Table(os.environ["USER_STATUS_TABLE"])
    return user_status_table.get_item(Key={"mobile_number": number}).get("Item")


def get_token(API_KEY, USERNAME, PASSWORD):
    """
    Get API token from Aarogya Setu it is valid for one hour and one succesful
    status request

    Parameters
    ----------
    API_KEY: API_KEY given by aarogya setu fetched from parameter store
    USERNAME: USERNAME for aarogya setu fetched from parameter store
    PASSWORD: PASSWORD for aarogya setu fetched from parameter store

    TODO: fix error message
    """

    url = TOKEN_URL
    headers = create_request_header(API_KEY)
    body = {"username": USERNAME, "password": PASSWORD}

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


def create_new_request(number, token, API_KEY, USERNAME, PASSWORD):
    """
    Create a new request with Aarogya Setu. Store both token and request id
    in the pending requests table.

    Parameters
    ----------
    number: User mobile number of the format "+919XXXXXXXXX"
    token: Request token given returned as reponse from TOKEN_URL
    API_KEY: API_KEY given by aarogya setu fetched from parameter store
    USERNAME: USERNAME for aarogya setu fetched from parameter store
    PASSWORD: PASSWORD for aarogya setu fetched from parameter store

    TODO: return error message
    """

    # get request id
    url = USER_STATUS_URL
    trace_id = create_trace_id()

    headers = create_request_header(API_KEY, token)
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


def get_status_content(number, token, request_id, API_KEY):
    """
    Get status for a pending request. Delete entry from pending request table
    if successfully gets status

    Parameters
    ----------
    number: User mobile number of the format "+919XXXXXXXXX"
    token: Request token given returned as reponse from TOKEN_URL
    API_KEY: API_KEY given by aarogya setu fetched from parameter store
    """

    url = USER_STATUS_BY_REQUEST_URL
    headers = create_request_header(API_KEY, token)
    body = {"requestId": request_id}

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        # TODO log error
        # error = json.loads(res.content)["error_message"]
        return None

    return res.json()


def decode_status(number, content, JWT_SECRET):
    """
    Decode user status using the jwt secret token and return an appropriate
    return status

    Parameters
    ----------
    number: User mobile number of the format "+919XXXXXXXXX"
    content: Encoded status returned as reponse from USER_STATUS_BY_REQUEST_URL
    JWT_SECRET: secret set in aarogya setu fetched from parameter store
    """

    if content["request_status"] == "Approved":
        coded_status = content["as_status"]
        status = jwt.decode(coded_status, JWT_SECRET)

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
    number: User mobile number of the format "+919XXXXXXXXX"
    """

    # check if status exists in ddb
    entry = check_user_status(number)

    # returned cached entry if it exists and status is not pending or denied
    if entry is not None and entry["statusCode"] == 200:
        return create_return_status(200, entry["message"])

    # fetch parameters and set in global variables for API
    JWT_SECRET, API_KEY, PASSWORD, USERNAME = fetch_parameters()

    # check ddb for pending request
    entry = get_pending_request(number)

    # create new request if it doesn't exist
    if entry is None:
        token = get_token(API_KEY, USERNAME, PASSWORD)

        if token is None:
            message = json.dumps(
                "Failed to get token from Aarogya Setu. Please try again"
            )
            return create_return_status(200, message)

        request_id = create_new_request(number, token, API_KEY, USERNAME, PASSWORD)

        if request_id is None:
            message = json.dumps(
                "Failed to get request id from Aarogya Setu. Please try again"
            )
            return create_return_status(200, message)

        store_pending_request(number, token, request_id)
    else:
        token = entry["token"]
        request_id = entry["request_id"]

    content = get_status_content(number, token, request_id, API_KEY)
    return_status = decode_status(number, content, JWT_SECRET)

    store_user_status(number, return_status)

    return return_status
