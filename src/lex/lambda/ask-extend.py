# Created by jongwonkim on 11/07/2017.


import boto3
import os
import logging
import json
import requests
from src.dynamodb.votes import DbVotes
from src.dynamodb.intents import DbIntents
from urllib.parse import urlencode
import requests


log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
db_votes = DbVotes(os.environ['VOTES_TABLE'])
sns = boto3.client('sns')


def retrieve_votes(event):
    db_response = db_votes.fetch_votes(event['sessionAttributes']['channel_id'])
    print('!!! db_response !!!')
    print(db_response)
    event['votes'] = db_response


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
    sec_first = 0
    sec_last = 0
    min_first = 0
    min_last = 0
    if event['currentIntent']['slots']['Extend']:
        slot_extend = event['currentIntent']['slots']['Extend']
        print('!!! SLOT RAW VALUE !!!')
        print(slot_extend)
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

    print('!!! TIMEOUT VALUE !!!')
    print(timeout)
    if timeout > 0:
        print('!!! SLOT FILLED !!!')

        if timeout > 1800:
            timeout = 1800  # Max 30 minutes

        activate_voting_timer(event, timeout)

        message = 'I extended the voting time for '

        minutes = int(timeout / 60)
        seconds = timeout - minutes * 60

        if minutes > 0:
            message += str(minutes) + ' minute(s) '
        if seconds > 0:
            message += str(seconds) + ' second(s).'

        message += ' I also sent a reminder to people who haven\'t voted yet.'

        print('!!! MESSAGE !!!')
        print(message)

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

    print(sns_event)

    sns.publish(
        TopicArn=os.environ['VOTING_TIMER_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def get_channel(event):
    params = {
        'token': event['sessionAttributes']['api_token'],
        'channel': event['sessionAttributes']['channel_id']
    }
    url = 'https://slack.com/api/channels.info?' + urlencode(params)
    response = requests.get(url).json()
    print('!!! RESPONSE !!!')
    print(response)
    if 'ok' in response and response['ok'] is True:
        event['channel'] = response['channel']
        return
    raise Exception('Failed to get a Slack channel info!')


def compose_fulfill_response(event):
    retrieve_votes(event)
    get_channel(event)
    if len(event['votes']) > 0:
        print('!!! VOTES AND CHANNEL !!!')
        print(event)
        print('!!! CALLBACK ID !!!')
        print(event['sessionAttributes']['callback_id'])
        callback_id = event['sessionAttributes']['callback_id'].split('|')
        prev_artists = ''
        if len(callback_id) > 1:
            prev_artists = callback_id[1]

        sns_event = {
            'team_id': event['sessionAttributes']['team_id'],
            'channel_id': event['sessionAttributes']['channel_id'],
            'token': event['sessionAttributes']['bot_token'],
            'api_token': event['sessionAttributes']['api_token'],
            'votes': event['votes'],
            'members': event['channel']['members'],
            'round': callback_id[0],
            'prev_artists': prev_artists,
        }
        # Please comment this out if you want to keep the voting buttons up.
        sns.publish(
            TopicArn=os.environ['EVALUATE_VOTES_SNS_ARN'],
            Message=json.dumps({'default': json.dumps(sns_event)}),
            MessageStructure='json'
        )

        # Update voting buttons as voting result!
        sns_event = {
            'token': event['sessionAttributes']['bot_token'],
            'channel': event['sessionAttributes']['channel_id'],
            'text': '',
            'attachments': [],
            'ts': event['intents']['vote_ts'],
            'as_user': True
        }
        print(sns_event)
        sns.publish(
            TopicArn=os.environ['UPDATE_MESSAGE_SNS_ARN'],
            Message=json.dumps({'default': json.dumps(sns_event)}),
            MessageStructure='json'
        )


        # New voting status (done) as a new message.
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
    else:
        # New voting status (done) as a new message.
        message = 'It seems like you guys hate me. Bye bye!'

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
