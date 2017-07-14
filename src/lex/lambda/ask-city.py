# Created by jongwonkim on 05/07/2017.

import boto3
import os
import logging
import json
import requests
from src.dynamodb.intents import DbIntents
from src.dynamodb.concerts import DbConcerts
from src.dynamodb.votes import DbVotes

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
db_concerts = DbConcerts(os.environ['CONCERTS_TABLE'])
db_votes = DbVotes(os.environ['VOTES_TABLE'])
sns = boto3.client('sns')


def publish_search_concert(event):
    sns_event = {
        'sessionAttributes': event['sessionAttributes'],
        'intents': event['intents']
    }
    return sns.publish(
        TopicArn=os.environ['SEARCH_CONCERT_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def compose_validate_response(event):
    event['intents']['current_intent'] = 'AskCity'
    if event['currentIntent']['slots']['City']:
        event['intents']['city'] = event['currentIntent']['slots']['City'].strip()
    if len(event['intents']['city']) > 0:
        event['intents']['current_intent'] = 'VotingConcert'

        # All required inputs are filled, now we starts searching process.
        publish_search_concert(event)

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


def compose_retry_response(event):
    event['intents']['current_intent'] = 'AskCity'
    message = "Hmm, I'm having trouble finding that city. Please try the format 'New York, NY' and try again."
    response = {
        'sessionAttributes': event['sessionAttributes'],
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': 'AskCity',
            'slotToElicit': 'City',
            'slots': {
                'City': None
            },
            'message': {
                'contentType': 'PlainText',
                'content': message
            }
        }
    }
    return response


def check_city(event):
    check = requests.get(os.environ['BIT_CITY_SEARCH'].format(
        "MyMusicMate",
        event['currentIntent']['slots']['City'].strip(),
        0
    )).json()
    if 'errors' in check and 'Unknown Location' in check['errors']:
        return False
    else:
        return True


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
        log.info(event)
        retrieve_intents(event)
        is_valid_city = check_city(event)
        print('!!! IS VALID CITY !!!')
        print(is_valid_city)
        if is_valid_city:
            response = compose_validate_response(event)
            store_intents(event)
            print('!!! RESET CONCERTS DB !!!')
            # db_concerts.remove_all(event['sessionAttributes']['channel_id'])
            db_votes.reset_votes(event['sessionAttributes']['channel_id'])
        else:
            response = compose_retry_response(event)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
