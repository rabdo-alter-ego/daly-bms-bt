import json
import requests
import time


splunk_url = "http://splunk.url"
bms_logger_token = "secret_token"


def post_to_splunk(event_list):
    headers = {
        "Authorization": f"Splunk {bms_logger_token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(
            splunk_url,
            headers=headers,
            data=json.dumps(event_list),
            timeout=30
        )
        if response.status_code == 200:
            print('successfully sent splunk events')
        else:
            print(f"Error code: {response.status_code}. Splunk returned: {response.text}")
    except Exception as e:
        print(f"Exception posting to Splunk: {e}")


def create_splunk_event(data):
    splunk_event = {
        "event": data,
        "time": int(time.time() * 1000)
    }

    return splunk_event