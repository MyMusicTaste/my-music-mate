# Created by jongwonkim on 06/07/2017.


import os
import logging
import json
from src.dynamodb.intents import DbIntents

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


def compose_validate_response(event):
    event['intents']['current_intent'] = 'AskArtist'
    if event['currentIntent']['slots']['Artist']:
        artists = event['currentIntent']['slots']['Artist'].strip().split(',')
        for artist in artists:
            if artist not in event['intents']['artists']:
                event['intents']['artists'].append(artist)
    if len(event['intents']['artists']) > 0:
        # To keep getting artists and store in the db session.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'ConfirmIntent',
            "intentName": "AskArtist",
            'slots': {
                'Artist': event['intents']['artists'][0]
            }
        }}
        return response
    else:   # First time getting an artist.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'Delegate',
            'slots': {
                'Artist': None
            }
        }}
        return response


# End of the AskArtist intention moves to the CreateChannel intention.
def compose_fulfill_response(event):
    event['intents']['current_intent'] = 'AskCity'
    response = {
        'sessionAttributes': event['sessionAttributes'],
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': 'AskCity',
            'slotToElicit': 'City',
            'slots': {
                'City': None
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
