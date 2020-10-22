import json
import requests
import jwt
import boto3
import os
import random
import string

from datetime import datetime, timedelta

# parameters
JWT_SECRET = None
API_KEY = None
USERNAME = None
PASSWORD = None

# global variables
RANDOM_STR_LEN = 5
USER_STATUS_EXPIRY_DAYS = 0.9
PENDING_REQUEST_EXPIRY_HOURS = 0.9
ssm = boto3.client("ssm")
ddb = boto3.resource("dynamodb")
user_status_table = ddb.Table(os.environ["USER_STATUS_TABLE"])
requests_table = ddb.Table(os.environ["REQUESTS_TABLE"])
mobile_number = None
token = None
request_id = None
headers = {
    "Access-Control-Allow-Headers": "Authorization",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST",
    "Access-Control-Allow-Credentials": True,
}
return_status = {"headers": headers}


def fetch_parameters():
    """
    Fetch Aarogya Setu API specific credentials and keys from parameter store
    and store it in global variables
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

    global JWT_SECRET, API_KEY, USERNAME, PASSWORD
    JWT_SECRET = parameters[JWT_KEY]
    API_KEY = parameters[API_KEY_KEY]
    PASSWORD = parameters[PASSWORD_KEY]
    USERNAME = parameters[USERNAME_KEY]


def store_return_status(return_status):
    """
    Takes a response adds an expiration time stamp to it and stores it in
    user status table.
    """

    expdate = datetime.now() + timedelta(days=USER_STATUS_EXPIRY_DAYS)
    expdate = str(int(expdate.timestamp()))

    # store status in ddb
    user_status_table.put_item(
        Item={
            "mobile_number": mobile_number,
            "message": return_status["body"],
            "expdate": expdate,
            "statusCode": return_status["statusCode"],
        },
    )


def check_mobile_number(number):
    """
    Check mobile number for COVID status. It first checks user status table
    for cached entry. If the entry is expired it makes a fresh request and then
    gets status for the request
    """

    global mobile_number, token, request_id, return_status
    mobile_number = number

    # check if status exists in ddb
    entry = user_status_table.get_item(Key={"mobile_number": mobile_number}).get("Item")

    # fetch parameters and set in global variables for API
    fetch_parameters()

    # returned cached entry if it exists and status is not pending or denied
    if entry is not None and entry["statusCode"] == 200:
        return_status["statusCode"] = 200
        return_status["body"] = entry["message"]
        return return_status

    # check ddb for pending request
    entry = requests_table.get_item(Key={"mobile_number": mobile_number}).get("Item")

    # create new request if it doesn't exist
    if entry is None:
        return_status = create_new_request()
        if return_status["statusCode"] == 203:
            store_return_status(return_status)
            return return_status
    else:
        token = entry["token"]
        request_id = entry["request_id"]

    return_status = get_status()
    store_return_status(return_status)
    return return_status


def create_new_request():
    """
    Create a new request with Aarogya Setu. Store both token and request id
    in the pending requests table.
    """

    global mobile_number, token, request_id, return_status

    # get token from api
    url = "https://api.aarogyasetu.gov.in/token"
    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }
    body = {"username": USERNAME, "password": PASSWORD}

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        print(res.content)
        error = json.loads(res.content)["error_message"]
        return_status["statusCode"] = 203
        return_status["body"] = json.dumps(
            "Aarogya Set API failed to get token. Please try again. Error: " + error
        )
        return return_status

    token = res.json()["token"]

    # get request id
    url = "https://api.aarogyasetu.gov.in/userstatus"
    timestamp = datetime.today().strftime("%Y-%m-%d-%H:%M:%S")
    randomstr = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=RANDOM_STR_LEN)
    )
    trace_id = timestamp + "-" + randomstr

    headers["Authorization"] = token
    body = {
        "phone_number": mobile_number,
        "trace_id": trace_id,
        "reason": "Office entry",
    }

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        print(res.content)
        error = json.loads(res.content)["error_message"]
        return_status["statusCode"] = 203
        return_status["body"] = json.dumps(
            "Aarogya Set API failed to make request. Please try again. Error: " + error
        )
        return return_status

    request_id = res.json()["requestId"]

    # log pending request in ddb
    expdate = datetime.now() + timedelta(hours=PENDING_REQUEST_EXPIRY_HOURS)
    expdate = str(int(expdate.timestamp()))
    requests_table.put_item(
        Item={
            "mobile_number": mobile_number,
            "token": token,
            "request_id": request_id,
            "expdate": expdate,
        },
    )

    return_status["statusCode"] = 200
    return_status["body"] = json.dumps(
        "Made request. Click get status button after user approves"
    )

    return return_status


def get_status():
    """
    Get status for a pending request. Delete entry from pending request table
    if successfully gets status
    """

    global mobile_number, token, request_id, return_status

    url = "https://api.aarogyasetu.gov.in/userstatusbyreqid"
    body = {"requestId": request_id}
    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "Authorization": token,
    }

    res = requests.post(url, data=json.dumps(body), headers=headers)
    if res.status_code != requests.codes.ok:
        print(res.content)
        error = json.loads(res.content)["error_message"]
        return_status["statusCode"] = 203
        return_status["body"] = json.dumps(
            "Aarogya Set API failed to get status. Please try again. Error: " + error
        )
        return return_status

    content = res.json()
    message = ""
    if content["request_status"] == "Approved":
        coded_status = content["as_status"]
        status = jwt.decode(coded_status, JWT_SECRET)

        message = status["as_status"]["message"]
        return_status["statusCode"] = 200
        return_status["body"] = json.dumps(message)

        # delete entry because token and request have expired
        requests_table.delete_item(Key={"mobile_number": mobile_number})

    elif content["request_status"] == "Pending":
        return_status["statusCode"] = 202
        return_status["body"] = json.dumps("Please wait for user to approve request")

    else:
        return_status["statusCode"] = 201
        return_status["body"] = json.dumps(
            "User has denied request. Please make a new request"
        )

    return return_status
