# Created by jongwonkim on 09/07/2017.

import os
import logging
import boto3
import json
import re
from src.dynamodb.votes import DbVotes
from src.dynamodb.teams import DbTeams
from urllib.parse import unquote

log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_votes = DbVotes(os.environ['VOTES_TABLE'])
db_teams = DbTeams(os.environ['TEAMS_TABLE'])
sns = boto3.client('sns')

#
# def get_slack_event(event):
#     return {
#         'slack': json.loads(event['body'])
#     }
#
#
# # Verify the token in the event matches the app's one.
# def verify_slack_token(event):
#     if 'token' in event['slack'] and event['slack']['token'] != os.environ['SLACK_APP_TOKEN']:
#         raise Exception('Slack bot api verification token does not match!')
#     return event
#
#
# # Check whether the team id is stored in the dynamodb.
# def get_slack_team(event):
#     db_response = db_teams.retrieve_team(event['slack']['team_id'])
#     if db_response['ok'] is False:
#         raise Exception('Cannot find team info bind to the Slack bot!')
#     event['team'] = db_response


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
#
#
# def check_bot_is_receiver(event):
#     message = event['slack']['event']['text']
#     bot_id = event['team']['bot']['bot_user_id']
#     caller_id = event['slack']['event']['user']
#     if bot_id == caller_id:
#         raise Exception('%s is Bot\'s own message.' % message)
#     is_bot_mentioned = re.match(r'^<@%s>.*$' % bot_id, message)
#     if is_bot_mentioned:
#         log.info('Bot %s is mentioned in %s' % (bot_id, message))
#         # Remove bot_user_id in case the message comes with a @{bot_name}.
#         event['slack']['event']['text'] = re.sub('<@%s>' % bot_id, '', message).strip()
#         return
#     raise Exception('Bot %s was not mentioned %s' % (bot_id, message))


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

#
# def publish_to_sns(event):
#     return sns.publish(
#         TopicArn=os.environ['SNS_ARN'],
#         Message=json.dumps({'default': json.dumps(event)}),
#         MessageStructure='json'
#     )


def get_slack_event(event):
    return {
        'slack': json.loads(unquote(event['body'][8:]))
    }


def get_team(event):
    event['teams'] = db_teams.retrieve_team(event['slack']['team']['id'])


def update_message(event):
    vote_count = len(event['votes'])
    print(vote_count)
    channel = event['slack']['channel']['id']
    print(channel)
    original_message = event['slack']['original_message']
    print(original_message)
    text = original_message['text']
    print(text)
    attachments = original_message['attachments']
    print(attachments)
    time_stamp = original_message['ts']
    print(time_stamp)
    bot_token = event['teams']['bot']['bot_access_token']
    # access_token = event['teams']['access_token']
    print(bot_token)

    print('attachments')
    print(attachments)
    if len(attachments) == 1:
        attachments.append({})
    if vote_count == 0:
        attachments[1] = {
            'text': 'No vote has been placed.'
        }
    elif vote_count == 1:
        attachments[1] = {
            'text': '1 vote has been placed.'
        }
    else:
        attachments[1] = {
            'text': '{} votes have been placed.'.format(vote_count)
        }

    sns_event = {
        'token': bot_token,
        'channel': channel,
        'text': text,
        'attachments': attachments,
        'ts': time_stamp,
        'as_user': True
    }
    print('!!! SNS EVENT !!!')
    print(sns_event)
    return sns.publish(
        TopicArn=os.environ['UPDATE_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def store_vote(event):
    db_votes.store_vote(item={
        'team_id': event['slack']['team']['id'],
        'channel_id': event['slack']['channel']['id'],
        'user_id': '_' + event['slack']['user']['id'],
        'event_id': event['slack']['actions'][0]['value']
    })


def retrieve_votes(event):
    db_response = db_votes.fetch_votes(event['slack']['channel']['id'])
    print('!!! db_response !!!')
    print(db_response)
    event['votes'] = db_response


def handler(event, context):
    log.info(json.dumps(event))
    response = {
        "statusCode": 200
    }
    try:
        event = get_slack_event(event)
        get_team(event)
        store_vote(event)
        retrieve_votes(event)
        update_message(event)
        log.info(response)
    except Exception as e:
        log.error(json.dumps({"message": str(e)}))
    finally:
        return response
