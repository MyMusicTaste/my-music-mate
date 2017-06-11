# Created by jongwonkim on 10/06/2017.

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
sns = boto3.client('sns')


def get_slack_event(event):
    return {
        'slack': json.loads(event['body'])
    }


def verify_token(event):
    if 'token' in event['slack'] and event['slack']['token'] != os.environ['VERIFICATION_TOKEN']:
        raise Exception('Slack bot api verification token does not match!')
    return True


def get_team(event):
    key = {
        'team_id': event['slack']['team_id']
    }
    table = dynamodb.Table(os.environ['TEAMS_TABLE'])
    response = table.get_item(Key=key)
    if 'Item' not in response:
        raise Exception('Cannot find team info bind to the Slack bot!')
    event['team'] = response['Item']
    return event


def check_for_mention(event):
    message = event['slack']['event']['text']
    bot_user_id = event['team']['bot']['bot_user_id']
    is_bot_user_mentioned = re.match(r'^<@%s>.*$' % bot_user_id, message)
    if is_bot_user_mentioned:
        log.info('Bot %s is mentioned in %s' % (bot_user_id, message))
        return event
    raise Exception('Bot %s was not mentioned %s' % (bot_user_id, message))


def publish_to_sns(event):
    return sns.publish(
        TopicArn=os.environ['SNS_ARN'],
        Message=json.dumps({'default': json.dumps(event)}),
        MessageStructure='json'
    )


def respond_to_slack(event):
    if 'type' in event['slack'] and event['slack']['type'] == 'url_verification':
        response = {
            "statusCode": 200,
            "body": json.dumps({"challenge": event['slack']['challenge']})
        }
        return response
    else:
        verify_token(event)
        get_team(event)
        check_for_mention(event)
        publish_to_sns(event)
        response = {
            "statusCode": 200
        }
        return response


def handler(event, context):
    log.info(json.dumps(event))
    try:
        slack_event = get_slack_event(event)
        log.info(json.dumps(slack_event))
        response = respond_to_slack(slack_event)
        log.info(json.dumps(response))
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response

