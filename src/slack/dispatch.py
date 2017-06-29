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
lex = boto3.client('lex-runtime')


def talk_lex(event):
    message = re.sub('<@', '@', event['slack']['event']['text'])
    message = re.sub('>', '', message)

    response = lex.post_text(
        botName=os.environ['LEX_NAME'],
        botAlias=os.environ['LEX_ALIAS'],
        userId=os.environ['AWS_ID'],
        sessionAttributes={
            "team_id": event['team']['team_id'],
            "channel": event['slack']['event']['channel']
        },
        inputText=message
    )
    return response


def post_message(event):
    lex_response = talk_lex(event)
    log.info(lex_response)
    if 'dialogState' in event and event['dialogState'] == 'ReadyForFulfillment':
        return lex_response
    params = {
        "token": event['team']['bot']['bot_access_token'],
        "channel": event['slack']['event']['channel'],
        "text": lex_response['message'],
    }
    url = 'https://slack.com/api/chat.postMessage?' + urlencode(params)
    response = requests.get(url)
    response_json = response.json()
    if 'ok' in response_json and response_json['ok'] is True:
        return response_json
    raise Exception('Failed to post a message to a Slack channel!')


def handler(event, context):
    log.info(json.dumps(event))
    try:
        post_message(json.loads(event['Records'][0]['Sns']['Message']))
        response = {
            "statusCode": 200,
            "body": json.dumps({"message": 'message has been sent successfully.'})
        }
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response
