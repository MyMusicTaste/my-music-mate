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


# def store_last_called_user(event, last_called):
#     table = dynamodb.Table(os.environ['LEX_USER_TABLE'])
#     return table.put_item(Item={
#         'team_id': event['slack']['team_id'],
#         'channel': event['slack']['channel'],
#         'user': event['slack']['user'],
#         'last_called': last_called
#     })
#
# def retrieve_last_called_user(event):
#     table = dynamodb.Table(os.environ['LEX_USER_TABLE'])
#     response = table.get_item(Key={
#         'team_id': event['slack']['team_id'],
#         'channel': event['slack']['channel'],
#         'user': event['slack']['user']
#     })
#     return response


def check_for_mention(event):
    message = event['slack']['event']['text']
    bot_user_id = event['team']['bot']['bot_user_id']
    slack_user_id = event['slack']['event']['user']
    is_bot_user_mentioned = re.match(r'^<@%s>.*$' % bot_user_id, message)
    # Save the last called user of the mentioner (only if the mentioner is not the bot).
    last_called_users = re.findall(r'^<@[A-Z1-9]\w+>', message)
    # if bot_user_id != slack_user_id and len(last_called_users) > 0:
    #     log.info('!!! store_last_called_user !!!')
    #     store_last_called_user(event, last_called_users[0])
    # else:
    #     response = retrieve_last_called_user(event)
    #     log.info('!!! retrieve_last_called_user !!!')
    #     log.info(response)
    #     if 'Item' in response and 'last_called' in response['Item']:
    #         if response['Item']['last_called'] == bot_user_id:
    #             is_bot_user_mentioned = true
    #             log.info('!!! is_bot_user_mentioned = true !!!')

    if is_bot_user_mentioned:
        log.info('Bot %s is mentioned in %s' % (bot_user_id, message))
        # Remove bot_user_id in case the message comes with a @{bot_name}.
        message = re.sub('<@%s>' % bot_user_id, '', message).strip()
        event['slack']['event']['text'] = message
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
            # check_for_mention(event)
            if event['team']['bot']['bot_user_id'] != event['slack']['event']['user']:  # Ignore bot's own message.
                publish_to_sns(event)
    except Exception as e:
        log.error(json.dumps({"message": str(e)}))
    finally:
        return response
