# Created by jongwonkim on 02/07/2017.


import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests
import re

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')
lex = boto3.client('lex-runtime')


def get_team(event):
    key = {
        'team_id': event['lex']['sessionAttributes']['team_id']
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
        "name": event['lex']['sessionAttributes']['room']
    }
    url = 'https://slack.com/api/channels.create?' + urlencode(params)
    response = requests.get(url)
    response_json = response.json()
    log.info(response_json)
    if 'ok' in response_json and response_json['ok'] is True:
        return response_json
    raise Exception('Failed to create a room on Slack!')


def handler(event, context):
    log.info(json.dumps(event))
    try:
        event = json.loads(event['Records'][0]['Sns']['Message'])
        get_team(event)
        create_room(event)
        response = {
            "statusCode": 200,
        }
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response
