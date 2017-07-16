# Created by jongwonkim on 05/07/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests
from src.dynamodb.intents import DbIntents


log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


def post_message_to_slack(event):
    unfurl_links = False
    unfurl_media = True
    as_user = False
    if 'unfurl_links' in event and event['unfurl_links'] is True:
        unfurl_links = True
    if 'unfurl_media' in event and event['unfurl_media'] is False:
        unfurl_media = False
    if 'as_user' in event and event['as_user'] is True:
        as_user = True
    if 'attachments' in event:
        params = {
            'token': event['token'],
            'channel': event['channel'],
            'text': event['text'],
            'attachments': event['attachments'],
            # 'parse': 'full',
            'unfurl_links': unfurl_links,
            'unfurl_media': unfurl_media,
            'as_user': as_user
        }
    else:
        params = {
            'token': event['token'],
            'channel': event['channel'],
            'text': event['text'],
            'as_user': as_user
        }
    if as_user is False:
        params['username'] = os.environ['BOT_NAME']
    url = 'https://slack.com/api/chat.postMessage?' + urlencode(params)
    response = requests.get(url).json()
    if 'ok' in response and response['ok'] is True:
        print('!!! PRE STORE TIME STAMP!!!')
        print(event)
        if 'attachments' in event and len(event['attachments']) > 0 and 'callback_id' in event['attachments'][0] and 'intents' in event:
            print('!!! STORE TIME STAMP!!!')
            print('!!! STORE TIME STAMP!!!')
            print('!!! STORE TIME STAMP!!!')
            print(event)
            print(response['ts'])
            print(event)
            print('!!! END STORE TIME STAMP!!!')
            print('!!! END STORE TIME STAMP!!!')
            print('!!! END STORE TIME STAMP!!!')
            event['intents']['vote_ts'] = response['ts']
        return
    raise Exception('Failed to post a message to a Slack channel!')


def store_intents(event):
    return db_intents.store_intents(
        keys={
            'team_id': event['team'],
            'channel_id': event['channel']
        },
        attributes=event['intents']
    )


def retrieve_intents(event):
    # if 'sessionAttributes' not in event:
    #     raise Exception('Required keys: `team_id` and `channel_id` are not provided.')
    event['intents'] = db_intents.retrieve_intents(
        event['team'],
        event['channel']
    )


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    try:
        if 'team' in event:
            retrieve_intents(event)
        post_message_to_slack(event)
        if 'team' in event:
            store_intents(event)
        log.info(response)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
    finally:
        return response
