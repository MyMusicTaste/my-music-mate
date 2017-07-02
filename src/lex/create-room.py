# Created by jongwonkim on 29/06/2017.


import os
import logging
import boto3
import json
import re
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')


def get_team(event):
    key = {
        'team_id': event['sessionAttributes']['team_id']
    }
    table = dynamodb.Table(os.environ['TEAMS_TABLE'])
    response = table.get_item(Key=key)
    if 'Item' not in response:
        raise Exception('Cannot find team info bind to the Slack bot!')
    event['team'] = response['Item']
    return event


def create_room(event):
    params = {
        "token": event['team']['access_token'],
        "name": event['sessionAttributes']['room']
    }
    url = 'https://slack.com/api/channels.create?' + urlencode(params)
    response = requests.get(url)
    response_json = response.json()
    event['slack'] = response_json
    # log.info(response_json)
    # return response_json
    # if 'ok' in response_json and response_json['ok'] is True:
    #     return response_json
    # raise Exception('Failed to create a room on Slack!')

def invite_members(event):
    for member in event['sessionAttributes']['invitees']:
        params = {
            'token': event['team']['access_token'],
            'channel': event['slack']['channel']['id'],
            "user": member
        }
        url = 'https://slack.com/api/channels.invite?' + urlencode(params)
        response = requests.get(url)


def create_session_placeholder(event):
    if not event['sessionAttributes']:
        event['sessionAttributes'] = {
            'team_id': 'T5K9TKQ3F',
            'channel': 'D5SH2NMML'
        }
    event['sessionAttributes']['room'] = None
    event['sessionAttributes']['invitees'] = []


def retrieve_session_attributes(event):
    table = dynamodb.Table(os.environ['SESSIONS_TABLE'])
    if 'sessionAttributes' not in event:
        raise Exception('`team_id` and `channel` are not provided.')
    response = table.get_item(Key={
        'team_id': event['sessionAttributes']['team_id'],
        'channel': event['sessionAttributes']['channel']
    })
    if 'Item' in response and 'room' in response['Item']:
        event['sessionAttributes']['room'] = response['Item']['room']
    else:
        event['sessionAttributes']['room'] = None
    if 'Item' in response and 'invitees' in response['Item']:
        event['sessionAttributes']['invitees'] = response['Item']['invitees']
    else:
        event['sessionAttributes']['invitees'] = []
    return event


def store_session_attributes(event):
    table = dynamodb.Table(os.environ['SESSIONS_TABLE'])
    return table.put_item(Item={
        'team_id': event['sessionAttributes']['team_id'],
        'channel': event['sessionAttributes']['channel'],
        'room': event['sessionAttributes']['room'],
        'invitees': event['sessionAttributes']['invitees']
    })


def compose_validate_response(event):
    slot_room = None
    if event['currentIntent']['slots']['Room']:
        slot_room = event['currentIntent']['slots']['Room']
        event['sessionAttributes']['room'] = slot_room
    if slot_room:   # Waiting for the user's confirmation.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'ConfirmIntent',
            "intentName": "CreateRoom",
            'slots': {
                'Room': slot_room
            }
        }}
        return response
    else:   # First time getting a Room name.
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'Delegate',
            'slots': {
                'Room': slot_room
            }
        }}
        return response


# End of the AddInvitee intention moves to the CreateChannel intention.
def compose_fulfill_response(event):
    result = ''
    if len(event['sessionAttributes']['invitees']) > 0:
        for i, invitee in enumerate(event['sessionAttributes']['invitees']):
            if result != '':
                if i < len(event['sessionAttributes']['invitees']) - 1:
                    result += ', '
                else:
                    result += ', and '
            result += '<@' + invitee + '>'

    get_team(event)
    create_room(event)

    log.info(event)

    if 'ok' in event['slack'] and event['slack']['ok'] is True:
        invite_members(event)

        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'Close',
            'fulfillmentState': 'Fulfilled',
            'message': {
                'contentType': 'PlainText',
                'content': 'You, and ' + result + ' are invited to a channel ' + event['sessionAttributes']['room'] + '.'
            }
        }}
        return response
    else:
        response = {
            'sessionAttributes': event['sessionAttributes'],
            'dialogAction': {
                'type': 'ElicitSlot',
                'message': {
                    'contentType': 'PlainText',
                    'content': "It seems like the channel already exists. Please choose a different name."
                },
                'intentName': 'CreateRoom',
                'slotToElicit': 'Room',
                'slots': {
                    'Room': None
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


def publish_to_sns(event):
    return sns.publish(
        TopicArn=os.environ['SNS_ARN'],
        Message=json.dumps({'default': json.dumps(event)}),
        MessageStructure='json'
    )


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200
    }
    try:
        create_session_placeholder(event)
        retrieve_session_attributes(event)
        # Terminating condition.
        if event['currentIntent'] is not None and event['currentIntent']['confirmationStatus'] == 'Confirmed':
            response = compose_fulfill_response(event)
        # Processing the user input.
        else:
            response = compose_validate_response(event)
        store_session_attributes(event)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
    finally:
        response['sessionAttributes'].pop('invitees')
        response['sessionAttributes'].pop('room')
        log.info(response)
        return response
