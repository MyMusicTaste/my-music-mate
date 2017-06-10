# Created by jongwonkim on 10/06/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)

log.debug('Invoking `install` function.')

dynamodb = boto3.resource('dynamodb')


def get_code(event):
    log.debug(json.dumps(event))
    code = None
    if event['queryStringParameters'] is not None and event['queryStringParameters']['code'] is not None:
        code = event['queryStringParameters']['code']
    return code


def request_token(code):
    log.debug(code)
    log.debug('Requesting token with' + code)
    log.debug(os.environ)
    if code is None:
        return None
    params = {
        "client_id": os.environ['CLIENT_ID'],
        "client_secret": os.environ['CLIENT_SECRET'],
        "code": code,
    }
    url = 'https://slack.com/api/oauth.access?' + urlencode(params)
    log.debug('Fetching' + code)
    response = requests.get(url)
    response_json = response.json()
    log.debug(response_json)
    if response_json['ok']:
        return response_json
    raise Exception('Slack API Error while requesting an API token!')


def save_response(response):
    table = dynamodb.Table(os.environ['TEAMS_TABLE'])
    return table.put_item(Item=response)


def handler(event, context):
    try:
        code = get_code(event)
        token_response = request_token(code)
        db_response = save_response(token_response)

        response = {
            "statusCode": 200,
            "body": json.dumps(db_response)
        }
        log.debug(response)
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": str(e)
        }
        log.error(response)
        return response

