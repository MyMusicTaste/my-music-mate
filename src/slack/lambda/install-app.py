# Created by jongwonkim on 10/06/2017.

# This lambda function will request a slack bot oauth2.0 token and store into a dynamodb table.

import os
import logging
from src.dynamodb.teams import DbTeams
import json
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)

db_teams = DbTeams(os.environ['TEAMS_TABLE'])


def request_token(event):
    params = {
        "client_id": os.environ['SLACK_APP_ID'],
        "client_secret": os.environ['SLACK_APP_SECRET'],
        "code": event['queryStringParameters']['code'],
    }
    url = 'https://slack.com/api/oauth.access?' + urlencode(params)
    event['team'] = requests.get(url).json()
    if 'ok' not in event['team'] or event['team']['ok'] is not True:
        raise Exception('Slack API Error while requesting an API token!')


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": os.environ['BOT_NAME'] + ' has been installed.'})
    }
    try:
        if event['queryStringParameters'] is not None and event['queryStringParameters']['code'] is not None:
            request_token(event)
            db_teams.store_team(event['team'])
        else:
            Exception('Slack API Error while fetching a temporary token!')
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
