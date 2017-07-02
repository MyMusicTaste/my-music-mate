# Created by jongwonkim on 29/06/2017.


import os
import logging
import boto3
import json
import re
# from urllib.parse import urlencode
# import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')


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
                    if len(event['sessionAttributes']['invitees'] < 3:
                        result += ', and '
                    else:
                        result += ' and '
            result += '<@' + invitee + '>'
    response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
        'type': 'Close',
        'fulfillmentState': 'Fulfilled',
        'message': {
            'contentType': 'PlainText',
            'content': result + ' are on a queue to be invited to a channel ' + event['sessionAttributes']['room'] + '.'
        }
    }}
    # response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
    #     'type': 'ElictSlot',
    #     'intentName': 'CreateChannel',
    #     'slotToElicit': 'Channel'
    # }}
    return response


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
