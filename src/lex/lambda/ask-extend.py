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
    timeout = 0  # Sec.
    min_found = True
    sec_found = True
    if event['currentIntent']['slots']['Extend']:
        slot_extend = event['currentIntent']['slots']['Extend']
        try:
            min_last = slot_extend.index('M')
            if min_last > -1:
                min_first = min_last
                while min_first >= 0:
                    min_first -= 1
                    if slot_extend[min_first].isdigit() is False:
                        break
                timeout += int(slot_extend[min_first + 1:min_last]) * 60  # Convert min to sec.
        except ValueError as e:
            min_found = False

        try:
            sec_last = slot_extend.index('S')
            if sec_last > -1:
                sec_first = sec_last
                while sec_first >= 0:
                    sec_first -= 1
                    if slot_extend[sec_first].isdigit() is False:
                        break
                timeout += int(slot_extend[sec_first + 1:sec_last])  # Convert min to sec.
        except ValueError as e:
            min_found = False
    if timeout > 0:
        print('!!! SLOT FILLED !!!')

        activate_voting_timer(event, timeout)

        message = 'I extended the voting time for '
        if min_found is True:
            message += slot_extend[min_first + 1:min_last] + ' minute(s) '
        if sec_found is True:
            message += slot_extend[sec_first + 1:sec_last] + ' second(s).'

        message += ' I also sent a reminder to people who haven\'t voted yet.'

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
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'ConfirmIntent',
            "intentName": "AskExtend",
            'slots': {
                'Extend': 'PT0S'
            }
        }}
        return response


        # print('!!! ElicitSlot !!!')
        # response = {
        #     'sessionAttributes': event['sessionAttributes'],
        #     'dialogAction': {
        #         'type': 'ElicitSlot',
        #         'intentName': 'AskExtend',
        #         'slotToElicit': 'Extend',
        #         'slots': {
        #             'Extend': None
        #         },
        #     }
        # }
        # return response

        # response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
        #     'type': 'Delegate',
        #     'slots': {
        #         'Extend': None
        #     }
        # }}
        # return response


def activate_voting_timer(event, timeout):
    event['intents']['timeout'] = str(timeout)
    sns_event = {
        'slack': {
            'team_id': event['sessionAttributes']['team_id'],
            'channel_id': event['sessionAttributes']['channel_id'],
            'api_token': event['sessionAttributes']['api_token'],
            'bot_token': event['sessionAttributes']['bot_token']
        },
        'callback_id': event['sessionAttributes']['callback_id'],
        'timeout': str(timeout)
    }

    return sns.publish(
        TopicArn=os.environ['VOTING_TIMER_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def compose_fulfill_response(event):
    message = 'Voting has completed. Please wait for a moment while I am collecting the result.'

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


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200
    }
    try:
        retrieve_intents(event)
        if event['currentIntent'] is not None and event['currentIntent']['confirmationStatus'] == 'Denied':
            response = compose_fulfill_response(event)
        else:
            response = compose_validate_response(event)
        # print('!!! INTENT !!!')
        # print(event)
        # if event['currentIntent'] is not None and event['currentIntent']['confirmationStatus'] == 'Confirmed':
        #     # Terminating condition.
        #     response = compose_fulfill_response(event)
        # else:
        # Processing the user input.

        store_intents(event)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
