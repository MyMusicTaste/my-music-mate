# Created by jongwonkim on 07/07/2017.


import os
import logging
import json
from src.dynamodb.intents import DbIntents

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


def compose_validate_response(event):
    event['intents']['current_intent'] = 'AskTaste'

    artists = []
    if event['currentIntent']['slots']['Artist']:
        artists = event['currentIntent']['slots']['Artist'].strip().split(',')
    for artist in artists:
        if artist not in event['intents']['artists']:
            event['intents']['artists'].append(artist)

    genres = []
    if event['currentIntent']['slots']['Genre']:
        genres = event['currentIntent']['slots']['Genre'].strip().split(',')
    for genre in genres:
        if genre not in event['intents']['genres']:
            event['intents']['genres'].append(genre)


    # Check whether boths slots are empty.
    # If so, pass the whole string value to the API
    # If something returns, then manually store into artist.
    # If not,

    # if event['currentIntent']['slots']['Artist'] and event['currentIntent']['slots']['Genre']:
    response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
        'type': 'ConfirmIntent',
        "intentName": "AskTaste",
        'slots': {
            'Artist': event['currentIntent']['slots']['Artist'],
            'Genre': event['currentIntent']['slots']['Genre']
        }
    }}
    # else:
    #     response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
    #         'type': 'Delegate',
    #         'slots': {
    #             'Artist': event['currentIntent']['slots']['Artist'],
    #             'Genre': event['currentIntent']['slots']['Genre']
    #         }
    #     }}
    return response

    # if event['currentIntent']['slots']['Genre']:
    #     genres = event['currentIntent']['slots']['Genre'].strip().split(',')
    #     for genre in genres:
    #         if genre not in event['intents']['genres']:
    #             event['intents']['genres'].append(genre)
    #     artist = None
    #     if len(event['intents']['artists']) > 0:
    #         artist = event['intents']['artists'][0]
    #     # To keep getting genres and store in the db session.
    #     response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
    #         'type': 'ConfirmIntent',
    #         "intentName": "AskTaste",
    #         'slots': {
    #             'Artist': artist,
    #             'Genre': event['intents']['genres'][0]
    #         }
    #     }}
    #     return response
    #
    # elif event['currentIntent']['slots']['Artist']:
    #     artists = event['currentIntent']['slots']['Artist'].strip().split(',')
    #     for artist in artists:
    #         if artist not in event['intents']['artists']:
    #             event['intents']['artists'].append(artist)
    #     genre = None
    #     if len(event['intents']['genres']) > 0:
    #         genre = event['intents']['genres'][0]
    #     # To keep getting artists and store in the db session.
    #     response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
    #         'type': 'ConfirmIntent',
    #         "intentName": "AskTaste",
    #         'slots': {
    #             'Artist': event['intents']['artists'][0],
    #             'Genre': genre
    #         }
    #     }}
    #     return response
    #
    # else:   # First time.
    #


# End of the AskTaste intention moves to the CreateChannel intention.
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
        if event['currentIntent'] is not None and event['currentIntent']['confirmationStatus'] == 'Denied' and event[
            'inputTranscript'].lower() in ['no', 'no thanks', 'nope', 'nah']: # TODO determine if proper strategy
            # Terminating condition.
            print("!!!! TERMINATOR !!!!")
            print(event)
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
