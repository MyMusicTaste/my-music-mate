# Created by jongwonkim on 29/06/2017.


import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests
import time
from src.dynamodb.intents import DbIntents
from src.dynamodb.teams import DbTeams

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
db_teams = DbTeams(os.environ['TEAMS_TABLE'])
sns = boto3.client('sns')


def publish_to_sns(event, message):
    sns_event = {
        'token': event['sessionAttributes']['bot_token'],
        'channel': event['sessionAttributes']['channel_id'],
        'text': message
    }
    return sns.publish(
        TopicArn=os.environ['SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def reserve_lounge(event):
    params = {
        "token": event['sessionAttributes']['api_token'],
        "name": event['intents']['lounge']['name']
    }
    url = 'https://slack.com/api/channels.create?' + urlencode(params)
    response = requests.get(url).json()
    if 'ok' in response and response['ok'] is True:
        event['intents']['lounge']['id'] = response['channel']['id']
        event['intents']['lounge']['name'] = response['channel']['name']
    else:
        event['intents']['lounge']['id'] = None
        event['intents']['lounge']['name'] = None


def invite_mates(event):
    for mate in event['intents']['mates']:
        params = {
            'token': event['sessionAttributes']['api_token'],
            'channel': event['intents']['lounge']['id'],
            "user": mate
        }
        url = 'https://slack.com/api/channels.invite?' + urlencode(params)
        requests.get(url)


def compose_validate_response(event):
    event['intents']['current_intent'] = 'ReserveLounge'
    slot_lounge = None
    if event['currentIntent']['slots']['Lounge']:
        event['intents']['lounge']['name'] = event['currentIntent']['slots']['Lounge']
    if event['intents']['lounge']['name']:
        # Waiting for the user's confirmation.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'ConfirmIntent',
            "intentName": "ReserveLounge",
            'slots': {
                'Lounge': event['intents']['lounge']['name']
            }
        }}
        return response
    else:   # First time getting a lounge name.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'Delegate',
            'slots': {
                'Lounge': None
            }
        }}
        return response


# End of the AddInvitee intention moves to the CreateChannel intention.
def compose_fulfill_response(event):
    reserve_lounge(event)
    # Lounge is successfully created.
    if event['intents']['lounge']['id']:
        db_response = db_teams.retrieve_team(event['sessionAttributes']['team_id'])

        mates_string = ''
        mates = event['intents']['mates']
        if len(mates) > 0:
            for i, mate in enumerate(mates):
                if len(mates) == 1:
                    mates_string += ' and '
                elif i == (len(mates) - 1):
                    mates_string += ', and '
                else:
                    mates_string += ', '
                mates_string += '<@' + mate + '>'

        # Post an invitation message to the host's Bot direct message channel.
        message = 'You' + mates_string + ' are ' +\
                  'invited to a channel `' + event['intents']['lounge']['name'] + '`.'
                  
        if db_response['ok']:
            event['intents']['mates'].append(db_response['bot']['bot_user_id'])
        invite_mates(event)
        # Composer response string.

        publish_to_sns(event, message)

        db_intents.switch_channel(
            channel_id=event['intents']['lounge']['id'],
            keys={
                'team_id': event['sessionAttributes']['team_id'],
                'channel_id': event['sessionAttributes']['channel_id']
            },
            attributes=event['intents']
        )

        event['sessionAttributes']['channel_id'] = event['intents']['lounge']['id']
        message = 'Hi, I am your music mate! ' +\
                  '<@' + event['intents']['host_id'] + '> ' +\
                  'asked me to invite you all for going to a concert together. ' +\
                  'For suggesting the best options for you, I want to know what kind of music you guys like.'
        publish_to_sns(event, message)

        time.sleep(2.5)
        response = {
            'sessionAttributes': event['sessionAttributes'],
            'dialogAction': {
                'type': 'ElicitSlot',
                'intentName': 'AskTaste',
                'slotToElicit': 'Genre',
                'slots': {
                    'Genre': None,
                    'Artist': None
                },
            }
        }

        # response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
        #     'type': 'Close',
        #     'fulfillmentState': 'Fulfilled',
        #     'message': {
        #         'contentType': 'PlainText',
        #         'content': 'Hi, I am your music mate!'
        #     }
        # }}
        return response
    else:
        event['intents']['lounge']['name'] = None
        response = {
            'sessionAttributes': event['sessionAttributes'],
            'dialogAction': {
                'type': 'ElicitSlot',
                'message': {
                    'contentType': 'PlainText',
                    'content': "It seems like the channel already exists. Please choose a different name."
                },
                'intentName': 'ReserveLounge',
                'slotToElicit': 'Lounge',
                'slots': {
                    'Lounge': None
                },
            }
        }
        return response
    # publish_to_sns({'lex': event})
    # response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
    #     'type': 'ElictSlot',
    #     'intentName': 'CreateChannel',
    #     'slotToElicit': 'Channel'
    # }}


# def publish_to_sns(event):
#     return sns.publish(
#         TopicArn=os.environ['SNS_ARN'],
#         Message=json.dumps({'default': json.dumps(event)}),
#         MessageStructure='json'
#     )


def retrieve_intents(event):
    if 'sessionAttributes' not in event:
        raise Exception('Required keys: `team_id` and `channel_id` are not provided.')
    event['intents'] = db_intents.retrieve_intents(
        event['sessionAttributes']['team_id'],
        event['sessionAttributes']['channel_id']
    )


def store_intents(event):
    event['intents']['host_id'] = event['sessionAttributes']['caller_id']
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
        if event['currentIntent'] is not None and event['currentIntent']['confirmationStatus'] == 'Confirmed':
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
        log.info(json.dumps(response))
        return response
