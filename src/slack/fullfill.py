# Created by jongwonkim on 11/06/2017.


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


def generate_message(event):
    if 'invocationSource' in event and event['invocationSource'] == 'FulfillmentCodeHook':
        if 'currentIntent' in event and event['currentIntent']['name'] == 'TodaysWeather':
            message = '☔ You ask me about the weather of ' + event['currentIntent']['slots']['City'] + ' at ' \
                      + event['currentIntent']['slots']['Time'] + '. Please wait just for a moment while I am asking to my friend lives in ' + event['currentIntent']['slots']['City'] + '.'
            event['message'] = message
            return event
    raise Exception('Lex has nothing to say!')


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


def post_message(event):
    params = {
        "token": event['team']['bot']['bot_access_token'],
        "channel": event['sessionAttributes']['channel'],
        "text": event['message'],
    }
    url = 'https://slack.com/api/chat.postMessage?' + urlencode(params)
    response = requests.get(url)
    response_json = response.json()
    if 'ok' in response_json and response_json['ok'] is True:
        return response_json
    raise Exception('Failed to post a message to a Slack channel!')


def api_request(event):
    params = {
        "q": event['currentIntent']['slots']['City'],
        "appid": '860ebb335e6d9f6c247b8ac5e592c461',
        "units": 'metric'
    }
    url = 'http://api.openweathermap.org/data/2.5/weather?' + urlencode(params)
    response = requests.get(url)
    response_json = response.json()
    log.info(response_json)
    message = '☔ Sorry, I couldn\'t get the weather info around ' + event['currentIntent']['slots']['Time'] \
              + '; however, the current weather of ' + response_json['name'] + ' is ' \
              + response_json['weather'][0]['description'] + '. Additionally, the temperature is ' + str(response_json['main']['temp']) \
              + '°C and the humidity is ' + str(response_json['main']['humidity']) + '%.'
    event['message'] = message
    return event


def handler(event, context):
    log.info(json.dumps(event))
    try:
        get_team(event)
        generate_message(event)
        post_message(event)
        api_request(event)
        time.sleep(1.5)   # hard sleep for smoother interaction.
        post_message(event)
        response = {
            "statusCode": 200,
            "body": json.dumps({"message": 'message has been sent successfully.'})
        }
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response
