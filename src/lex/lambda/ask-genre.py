# Created by jongwonkim on 06/07/2017.


import os
import logging
import json
from src.dynamodb.intents import DbIntents

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


def compose_validate_response(event):
    event['intents']['current_intent'] = 'AskGenre'
    if event['currentIntent']['slots']['Genre']:
        genres = event['currentIntent']['slots']['Genre'].strip().split(',')
        for genre in genres:
            if genre not in event['intents']['genres']:
                event['intents']['genres'].append(genre)
    if len(event['intents']['genres']) > 0:
        # To keep getting genres and store in the db session.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'ConfirmIntent',
            "intentName": "AskGenre",
            'slots': {
                'Genre': event['intents']['genres'][0]
            }
        }}
        return response
    else:   # First time getting an genre.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'Delegate',
            'slots': {
                'Genre': None
            }
        }}
        return response


# End of the AskGenre intention moves to the CreateChannel intention.
def compose_fulfill_response(event):
    event['intents']['current_intent'] = 'AskArtist'
    response = {
        'sessionAttributes': event['sessionAttributes'],
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': 'AskArtist',
            'slotToElicit': 'Artist',
            'slots': {
                'Artist': None
            },
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
        if event['currentIntent'] is not None and event['currentIntent']['confirmationStatus'] == 'Denied':
            # Terminating condition.
            response = compose_fulfill_response(event)
        else:
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
