# Created by jongwonkim on 09/07/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)


def update_message_to_slack(event):
    as_user = False
    if 'as_user' in event:
        as_user = event['as_user']
    if 'attachments' in event:
        params = {
            'token': event['token'],
            'channel': event['channel'],
            'text': event['text'],
            'attachments': event['attachments'],
            'ts': event['ts'],
            'as_user': as_user
        }
    else:
        params = {
            'token': event['token'],
            'channel': event['channel'],
            'text': event['text'],
            'ts': event['ts'],
            'as_user': as_user
        }

    log.info('!!! PARAMS !!!')
    log.info(urlencode(params))
    print('!!! PARAMS !!!')
    print(urlencode(params))
    url = 'https://slack.com/api/chat.update?' + urlencode(params)
    response = requests.get(url).json()
    print('!!! RESPONSE !!!')
    print(response)
    if 'ok' in response and response['ok'] is True:
        return
    raise Exception('Failed to update a message to a Slack channel!')


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    # try:
    log.info('!!! EVENT !!!')
    log.info(event)
    print('!!! EVENT !!!')
    print(event)
    update_message_to_slack(event)
    log.info(response)
    return response
    # except Exception as e:
    #     response = {
    #         "statusCode": 400,
    #         "body": json.dumps({"message": str(e)})
    #     }
    #     log.error(response)
    # finally:
    #     return response
