# Created by jongwonkim on 10/06/2017.

import os
import logging
import boto3
import json
import re
# from urllib.parse import urlencode
# import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Put event coming from Slack into `slack` dictionary. We keep this format since we also want to include other data
# ex> dynamodb responses into the event object.
def get_slack_event(event):
    return {
        'slack': json.loads(event['body'])
    }


# Verify the token exists in the dynamodb.
def verify_token(event):
    if 'token' in event['slack'] and event['slack']['token'] != os.environ['VERIFICATION_TOKEN']:
        raise Exception('Slack bot api verification token does not match!')
    return event


# Check whether the team id is stored in the dynamodb.
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
    log.info('message: ', message)
    bot_user_id = event['team']['bot']['bot_user_id']
    is_bot_user_mentioned = re.match(r'^<@%s>.*$' % bot_user_id, message)
    if is_bot_user_mentioned:
        # Remove bot_user_id in case the message comes with a @{bot_name}.
        event['slack']['event']['text'] = re.sub('@%s' % bot_user_id, '', message).strip()
        log.info('Bot %s is mentioned in %s' % (bot_user_id, message))
        return event
    raise Exception('Bot %s was not mentioned %s' % (bot_user_id, message))


def publish_to_sns(event):
    return sns.publish(
        TopicArn=os.environ['SNS_ARN'],
        Message=json.dumps({'default': json.dumps(event)}),
        MessageStructure='json'
    )


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200
    }
    try:
        event = get_slack_event(event)
        # Response to Slack challenge.
        if 'type' in event['slack'] and event['slack']['type'] == 'url_verification':
            response['body'] = json.dumps({"challenge": event['slack']['challenge']})
        else:
            # Response to an actual slack event.
            verify_token(event)
            get_team(event)
            log.info(json.dumps(event))
            check_for_mention(event)
            if event['team']['bot']['bot_user_id'] != event['slack']['event']['user']:  # Ignore bot's own message.
                publish_to_sns(event)
    except Exception as e:
        log.error(json.dumps({"message": str(e)}))
    finally:
        return response

