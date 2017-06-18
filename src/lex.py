# Created by jongwonkim on 16/06/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests
import re
import time

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')
lex = boto3.client('lex-models')


def get_lex_bot():
    return lex.get_bot(
        name=os.environ['LEX_NAME'],
        versionOrAlias='$LATEST'
    )


def put_lex_bot(checksum):
    if checksum is None:
        return lex.put_bot(
            name=os.environ['LEX_NAME'],
            description='Lex for the MMT Slack bot.',
            intents=[
                {
                    'intentName': 'TodaysWeather',
                    'intentVersion': '$LATEST'
                },
            ],
            clarificationPrompt={
                'messages': [
                    {
                        'contentType': 'PlainText',
                        'content': 'Sorry, I didn\'t understand. Please repeat.'
                    },
                ],
                'maxAttempts': 5
            },
            abortStatement={
                'messages': [
                    {
                        'contentType': 'PlainText',
                        'content': 'Sorry, you are not listening at all. See ya!'
                    },
                ]
            },
            idleSessionTTLInSeconds=300,
            processBehavior='BUILD',
            locale='en-US',
            childDirected=False
        )
    else:
        return lex.put_bot(
            name=os.environ['LEX_NAME'],
            description='Lex for the MMT Slack bot.',
            intents=[
                {
                    'intentName': 'TodaysWeather',
                    'intentVersion': '$LATEST'
                },
            ],
            clarificationPrompt={
                'messages': [
                    {
                        'contentType': 'PlainText',
                        'content': 'Sorry, I didn\'t understand. Please repeat.'
                    },
                ],
                'maxAttempts': 5
            },
            abortStatement={
                'messages': [
                    {
                        'contentType': 'PlainText',
                        'content': 'Sorry, you are not listening at all. See ya!'
                    },
                ]
            },
            idleSessionTTLInSeconds=300,
            checksum=checksum,
            processBehavior='BUILD',
            locale='en-US',
            childDirected=False
        )


def createLexAlias():
    response = client.put_bot_alias(
        name=os.environ['LEX_ALIAS'],
        botVersion='$LATEST',
        botName=os.environ['LEX_NAME'],
        checksum='string'
    )
    return response


def handler(event, context):
    log.info(json.dumps(event))
    lex_bot_checksum = None
    try:
        lex_response = get_lex_bot()
        lex_bot_checksum = lex_response['checksum']
    except lex.exceptions.NotFoundException as e:
        lex_bot_checksum = None
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response

    try:
        lex_response = put_lex_bot(lex_bot_checksum)
        response = {
            "statusCode": 200,
            "body": json.dumps({"message": 'the bot was updated successfully.'})
        }
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response
