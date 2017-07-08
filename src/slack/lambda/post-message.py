# Created by jongwonkim on 05/07/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)


def post_message_to_slack(event):
    if 'attachments' in event:
        params = {
            'token': event['token'],
            'channel': event['channel'],
            'text': event['text'],
            'attachments': event['attachments']
        }
    else:
        params = {
            'token': event['token'],
            'channel': event['channel'],
            'text': event['text']
        }
    url = 'https://slack.com/api/chat.postMessage?' + urlencode(params)
    response = requests.get(url).json()
    if 'ok' in response and response['ok'] is True:
        return
    raise Exception('Failed to post a message to a Slack channel!')


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    try:
        post_message_to_slack(event)
        log.info(response)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
    finally:
        return response
