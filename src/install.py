# Created by jongwonkim on 10/06/2017.

# This lambda function will request a slack bot oauth2.0 token and store into a dynanodb table.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')


def get_code(event):
    code = None
    if event['queryStringParameters'] is not None and event['queryStringParameters']['code'] is not None:
        code = event['queryStringParameters']['code']
    return code


def request_token(code):
    if code is None:
        Exception('Slack API Error while fetching a temporary token!')
    params = {
        "client_id": os.environ['CLIENT_ID'],
        "client_secret": os.environ['CLIENT_SECRET'],
        "code": code,
    }
    url = 'https://slack.com/api/oauth.access?' + urlencode(params)
    response = requests.get(url)
    response_json = response.json()
    if response_json['ok']:
        return response_json
    raise Exception('Slack API Error while requesting an API token!')


def save_response(response):
    table = dynamodb.Table(os.environ['TEAMS_TABLE'])
    return table.put_item(Item=response)


def handler(event, context):
    log.info(json.dumps(event))
    try:
        code = get_code(event)
        token_response = request_token(code)
        log.info(json.dumps(token_response))
        db_response = save_response(token_response)
        log.info(json.dumps(db_response))

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": os.environ['BOT_NAME'] + ' has been installed.'})
        }
        log.info(response)
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response

