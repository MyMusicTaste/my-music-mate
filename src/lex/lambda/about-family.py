# Created by jongwonkim on 17/07/2017.


import os
import logging
import json
import re
import boto3
from src.dynamodb.intents import DbIntents
import time

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
sns = boto3.client('sns')


def publish_to_sns(event, message):
    sns_event = {
        'token': event['sessionAttributes']['bot_token'],
        'channel': event['sessionAttributes']['channel_id'],
        'text': message,
        'unfurl_links': True
    }
    return sns.publish(
        TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def retrieve_intents(event):
    if 'sessionAttributes' not in event:
        raise Exception('Required keys: `team_id` and `channel_id` are not provided.')
    event['intents'] = db_intents.retrieve_intents(
        event['sessionAttributes']['team_id'],
        event['sessionAttributes']['channel_id']
    )


def compose_fulfill_response(event):
    family = event['currentIntent']['slots']['Family']
    print('!!! FAMILY !!!')
    print(family)
    message = family
    cache_buster = str(time.time())

    if 'cousin' in family: # brother in law
        message = 'I have two cousins.'
        message += '<{}/paul.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
        message += '<{}/taeheon.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
    elif 'grand' in family and ('father' in family or 'pa' in family):
        message = '<{}/jinwook.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
    elif 'god' in family and 'father' in family:
        message = '<{}/jay.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
    elif 'dad' in family or 'father' in family:
        message = '<{}/jongwon.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
    elif 'mom' in family or 'mother' in family:
        message = '<{}/moonju.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
    elif 'uncle' in family:
        message = 'I have two uncles.'
        message += '<{}/hong.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
        message += '<{}/jaekeon.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
    elif 'brother' in family or 'sister' in family or 'sibling' in family:
        message = '<{}/bopbot.html?time={}| >'.format(os.environ['DEVS_BUCKET_ADDRESS'], cache_buster)
    else:
        message = 'I don\'t have any {}.'.format(family)

    print('!!! SEND SNS MESSAGE !!!')
    publish_to_sns(event, message)

    print('!!! FIND PREVIOUS INTENT !!!')

    prev_intent = event['intents']['current_intent']
    print(prev_intent)

    if prev_intent == 'AskCity':
        print('!!! ASK CITY !!!')
        response = {
            'sessionAttributes': event['sessionAttributes'],
            'dialogAction': {
                'type': 'ElicitSlot',
                'intentName': 'AskCity',
                'slotToElicit': 'City',
                'slots': {
                    'City': None
                }
            }
        }
    elif prev_intent == 'AskExtend':
        print('!!! ASK EXTEND !!!')
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'ConfirmIntent',
            'message': {
                'contentType': 'PlainText',
                'content': 'Now, tell me know if you need to extend the voting time.'
            },
            'intentName': 'AskExtend',
            'slots': {
                'Extend': 'PT0S'
            }
        }}
    elif prev_intent == 'AskTaste':
        print('!!! ASK TASTE !!!')
        response = {'sessionAttributes': event['sessionAttributes'], 'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': 'AskTaste',
            'slots': {
                'Artist': None,
                'Genre': None
            }
        }}
    elif prev_intent == 'InviteMate':
        print('!!! INVITE MATE !!!')
        response = {
            'sessionAttributes': event['sessionAttributes'],
            'dialogAction': {
                'type': 'ElicitSlot',
                'intentName': 'InviteMate',
                'slotToElicit': 'Mate',
                'message': {
                    'contentType': 'PlainText',
                    'content': 'Unless you want to know more about my family, tell me whom would you like to invite.'
                },
                'slots': {
                    'Mate': None
                }
            }
        }
    elif prev_intent == 'ReserveLounge':
        print('!!! RESERVE LOUNGE !!!')
        response = {
            'sessionAttributes': event['sessionAttributes'],
            'dialogAction': {
                'type': 'ElicitSlot',
                'intentName': 'ReserveLounge',
                'slotToElicit': 'Lounge',
                'message': {
                    'contentType': 'PlainText',
                    'content': 'Do you want to know about my family more? or do you want to choose a channel name?'
                },
                'slots': {
                    'Lounge': None
                }
            }
        }
    else:
        response = {
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled'
            }
        }
    return response


    # response = {
    #     'sessionAttributes': event['sessionAttributes'],
    #     'dialogAction': {
    #         'type': 'ElicitSlot',
    #         'intentName': 'AskCity',
    #         'slotToElicit': 'City',
    #         'slots': {
    #             'City': None
    #         },
    #     }
    # }
    # return response

    # response = {
    #     'dialogAction': {
    #         'type': 'Close',
    #         'fulfillmentState': 'Fulfilled',
    #         'message': {
    #             'contentType': 'PlainText',
    #             'content': message
    #         }
    #     }
    # }
    # return response


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200
    }
    try:
        retrieve_intents(event)
        response = compose_fulfill_response(event)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
