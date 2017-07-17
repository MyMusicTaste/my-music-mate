# Created by jongwonkim on 10/06/2017.

import os
import logging
import boto3
import json
import re
from src.dynamodb.teams import DbTeams
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_teams = DbTeams(os.environ['TEAMS_TABLE'])
sns = boto3.client('sns')

# Put event coming from Slack into `slack` dictionary. We keep this format since we also want to include other data
# ex> dynamodb responses into the event object.


def get_slack_event(event):
    return {
        'slack': json.loads(event['body'])
    }


# Verify the token in the event matches the app's one.
def verify_slack_token(event):
    if 'token' in event['slack'] and event['slack']['token'] != os.environ['SLACK_APP_TOKEN']:
        raise Exception('Slack bot api verification token does not match!')
    return event


# Check whether the team id is stored in the dynamodb.
def get_slack_team(event):
    db_response = db_teams.retrieve_team(event['slack']['team_id'])
    if db_response['ok'] is False:
        raise Exception('Cannot find team info bind to the Slack bot!')
    event['team'] = db_response


# def store_last_called_user(event, last_called):
#     last_called = re.sub('<@', '', last_called)
#     last_called = re.sub('>', '', last_called)
#     table = dynamodb.Table(os.environ['TALKS_TABLE'])
#     return table.put_item(Item={
#         'team_id': event['slack']['team_id'],
#         'user': event['slack']['event']['user'],
#         'last_called': last_called
#     })
#
#
# def retrieve_last_called_user(event):
#     table = dynamodb.Table(os.environ['TALKS_TABLE'])
#     return table.get_item(Key={
#         'team_id': event['slack']['team_id'],
#         'user': event['slack']['event']['user']
#     })


def check_bot_is_receiver(event):
    message = event['slack']['event']['text']
    bot_id = event['team']['bot']['bot_user_id']
    caller_id = event['slack']['event']['user']
    if bot_id == caller_id:
        raise Exception('%s is Bot\'s own message.' % message)
    is_bot_mentioned = re.match(r'^<@%s>.*$' % bot_id, message)

    print('!!! is_bot_mentioned !!!')
    print(is_bot_mentioned)
    if is_bot_mentioned is not True:
        params = {
            'token': event['team']['access_token'],
            'channel': event['slack']['event']['channel']
        }
        url = 'https://slack.com/api/channels.info?' + urlencode(params)
        response = requests.get(url).json()
        print(response)
        if 'channel' in response:
            members = response['channel']['members']
            print('!!! CHECK CHANNEL !!!')
            print(members)
            print(bot_id)
            print(caller_id)
            print('!!! CHECK CHANNEL !!!')
            if len(members) == 2 and bot_id in members and caller_id in members:
                is_bot_mentioned = True
        elif 'error' in response and response['error'] == 'channel_not_found':
            is_bot_mentioned = True

    if is_bot_mentioned:
        log.info('Bot %s is mentioned in %s' % (bot_id, message))
        # Remove bot_user_id in case the message comes with a @{bot_name}.
        event['slack']['event']['text'] = re.sub('<@%s>' % bot_id, '', message).strip()
        return
    raise Exception('Bot %s was not mentioned %s' % (bot_id, message))


# def check_for_mention(event):
#     message = event['slack']['event']['text']
#     bot_user_id = event['team']['bot']['bot_user_id']
#     slack_user_id = event['slack']['event']['user']
#     is_bot_user_mentioned = re.match(r'^<@%s>.*$' % bot_user_id, message)
#     # Save the last called user of the mentioner (only if the mentioner is not the bot).
#     last_called_users = re.findall(r'^<@[A-Z1-9]\w+>', message)
#     if bot_user_id != slack_user_id and len(last_called_users) > 0:
#         store_last_called_user(event, last_called_users[0])
#     else:
#         response = retrieve_last_called_user(event)
#         if 'Item' in response and 'last_called' in response['Item']:
#             if response['Item']['last_called'] == bot_user_id:
#                 is_bot_user_mentioned = True
#
#     if is_bot_user_mentioned:
#         log.info('Bot %s is mentioned in %s' % (bot_user_id, message))
#         # Remove bot_user_id in case the message comes with a @{bot_name}.
#         message = re.sub('<@%s>' % bot_user_id, '', message).strip()
#         event['slack']['event']['text'] = message
#         return event
#     raise Exception('Bot %s was not mentioned %s' % (bot_user_id, message))


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
        print(event)
        if 'type' in event['slack'] and event['slack']['type'] == 'url_verification':
            # Response to Slack challenge.
            response['body'] = json.dumps({"challenge": event['slack']['challenge']})
        else:
            # Response to an actual slack event.
            verify_slack_token(event)
            get_slack_team(event)
            check_bot_is_receiver(event)
            publish_to_sns(event)
    except Exception as e:
        log.error(json.dumps({"message": str(e)}))
    finally:
        log.info(response)
        return response
