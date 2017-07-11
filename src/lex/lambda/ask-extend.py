# Created by jongwonkim on 11/07/2017.


import boto3
import os
import logging
import json
import requests
from src.dynamodb.intents import DbIntents

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
sns = boto3.client('sns')


def retrieve_intents(event):
    if 'sessionAttributes' not in event:
        raise Exception('Required keys: `team_id` and `channel_id` are not provided.')
    event['intents'] = db_intents.retrieve_intents(
        event['sessionAttributes']['team_id'],
        event['sessionAttributes']['channel_id']
    )


def store_intents(event):
    return db_intents.store_intents(
        keys={
            'team_id': event['sessionAttributes']['team_id'],
            'channel_id': event['sessionAttributes']['channel_id']
        },
        attributes=event['intents']
    )


def compose_validate_response(event):
    event['intents']['current_intent'] = 'AskExtend'
    slot_extend = None
    if event['currentIntent']['slots']['Extend']:
        slot_extend = event['currentIntent']['slots']['Extend']
        print('!!! SLOT !!!')
        print(slot_extend)
    if slot_extend:
        print('!!! SLOT FILLED !!!')
        event['intents']['timeout'] += 30  # Test code.

        message = 'I am extending time 30 more seconds'
        response = {
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled',
                'message': {
                    'contentType': 'PlainText',
                    'content': message
                }
            }
        }
        return response
    else:   # First time getting a extend time.
        print('!!! ElicitSlot !!!')
        response = {
            'sessionAttributes': event['sessionAttributes'],
            'dialogAction': {
                'type': 'ElicitSlot',
                'intentName': 'AskExtend',
                'slotToElicit': 'Extend',
                'slots': {
                    'Extend': None
                },
            }
        }
        return response

        # response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
        #     'type': 'Delegate',
        #     'slots': {
        #         'Extend': None
        #     }
        # }}
        # return response


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200
    }
    try:
        retrieve_intents(event)
        print('!!! INTENT !!!')
        print(event)
        # if event['currentIntent'] is not None and event['currentIntent']['confirmationStatus'] == 'Confirmed':
        #     # Terminating condition.
        #     response = compose_fulfill_response(event)
        # else:
        # Processing the user input.
        response = compose_validate_response(event)
        store_intents(event)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
