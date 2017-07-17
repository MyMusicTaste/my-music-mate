# Created by jongwonkim on 17/07/2017.


import os
import logging
import json
import re
import boto3
from src.dynamodb.intents import DbIntents

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
sns = boto3.client('sns')


def publish_to_sns(event, message):
    sns_event = {
        'token': event['sessionAttributes']['bot_token'],
        'channel': event['sessionAttributes']['channel_id'],
        'text': message
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
    message = 'My name is MyMusicMate and I was born in July, 2017. ' \
              'I was born of a love of music and technology in the city of Seoul, South Korea. ' \
              'My passions include reading, hanging out with my best friends Lex and Slack, ' \
              'and spending time with my family. Speaking of family, I have [a grandpa, two uncles, ' \
              'a mom, a dad, a god father, two cousins, and a sibling]. ' \
              'If you\'d like to know who they are, don\'t hesitate to ask :)'
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
