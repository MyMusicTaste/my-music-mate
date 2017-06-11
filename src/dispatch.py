# Created by jongwonkim on 11/06/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests
import re

log = logging.getLogger()
log.setLevel(logging.DEBUG)


def post_message(event):
    bot_user_id = event['team']['bot']['bot_user_id']
    message = re.sub('<@%s>' % bot_user_id, '', event['slack']['event']['text']).strip()

    params = {
        "token": event['team']['bot']['bot_access_token'],
        "channel": event['slack']['event']['channel'],
        "text": message,
    }
    url = 'https://slack.com/api/chat.postMessage?' + urlencode(params)
    response = requests.get(url)
    return response.json()


def handler(event, context):
    log.info(json.dumps(event))
    slack_event = json.loads(event['Records'][0]['Sns']['Message'])
    log.info(slack_event)
    api_response = post_message(slack_event)
    log.info(api_response)
    response = {
        "statusCode": 200
    }
    return response


