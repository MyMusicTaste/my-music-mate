# Created by jongwonkim on 05/07/2017.


import os
import logging
import json
from src.dynamodb.intents import DbIntents

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


def compose_validate_response(event):
    event['intents']['current_intent'] = 'AskCity'
    if event['currentIntent']['slots']['City']:
        event['intents']['city'] = event['currentIntent']['slots']['City'].strip().split(',')[0]
    if len(event['intents']['city']) > 0:
        event['intents']['current_intent'] = 'VotingConcert'
        message = 'I am selecting the best options for you guys, and then we will start the voting process real soon.'
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


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200
    }
    try:
        retrieve_intents(event)
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
