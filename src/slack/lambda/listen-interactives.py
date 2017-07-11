# Created by jongwonkim on 09/07/2017.

import os
import logging
import boto3
import json
import re
from src.dynamodb.votes import DbVotes
from src.dynamodb.teams import DbTeams
from urllib.parse import unquote
from urllib.parse import urlencode
import requests
import time



log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_votes = DbVotes(os.environ['VOTES_TABLE'])
db_teams = DbTeams(os.environ['TEAMS_TABLE'])
sns = boto3.client('sns')


def get_slack_event(event):
    event['body'] = event['body'].replace('+', '%20')   # Hotfix for converting `+` into ` ` space.
    return {
        'slack': json.loads(unquote(event['body'][8:]))
    }


def get_channel(event):
    params = {
        'token': event['teams']['access_token'],
        'channel': event['slack']['channel']['id']
    }
    url = 'https://slack.com/api/channels.info?' + urlencode(params)
    response = requests.get(url).json()
    print('!!! RESPONSE !!!')
    print(response)
    if 'ok' in response and response['ok'] is True:
        event['channel'] = response['channel']
        return
    raise Exception('Failed to get a Slack channel info!')


def get_team(event):
    event['teams'] = db_teams.retrieve_team(event['slack']['team']['id'])


def update_message(event):
    vote_count = len(event['votes'])
    channel = event['slack']['channel']['id']
    original_message = event['slack']['original_message']
    text = original_message['text']
    attachments = original_message['attachments']
    time_stamp = original_message['ts']
    bot_token = event['teams']['bot']['bot_access_token']
    access_token = event['teams']['access_token']

    member_count = len(event['channel']['members'])

    print('attachments')
    print(attachments)

    # attachments[0]['actions'] voting actions

    visited_concerts = {}
    for vote in event['votes']:
        if vote['event_id'] not in visited_concerts:
            visited_concerts[vote['event_id']] = 1
        else:
            visited_concerts[vote['event_id']] += 1

    for action in attachments[0]['actions']:
        found = False
        for key in visited_concerts:
            if action['value'] == key:
                found = True
                action['text'] = '[' + str(visited_concerts[key]) + '] ' + action['name']
        if found is False:
            action['text'] = '[0] ' + action['name']

    # We don't need to show the extra message since we showed how many votes each concert gets.
    # if len(attachments) == 1:
    #     attachments.append({})
    # if vote_count == 0:
    #     attachments[1] = {
    #         'text': 'No vote has been placed.'
    #     }
    # elif vote_count == 1:
    #     attachments[1] = {
    #         'color': '#3AA3E3',
    #         'text': '1 vote has been placed.'
    #     }
    # else:
    #     attachments[1] = {
    #         'color': '#3AA3E3',
    #         'text': '{} votes have been placed.'.format(vote_count)
    #     }

    # For testing purpose, I won't override the voting message.
    if vote_count == member_count - 1:  # Excluding the bot from voters.
        text = 'Voting is completed. I will show you the result shortly.'
        attachments = None
        callback_id = event['slack']['callback_id'].split('|')
        prev_artists = ''
        if len(callback_id) > 1:
            prev_artists = callback_id[1]

        sns_event = {
            'team_id': event['slack']['team']['id'],
            'channel_id': event['slack']['channel']['id'],
            'token': bot_token,
            'api_token': access_token,
            'votes': event['votes'],
            'members': event['channel']['members'],
            'round': callback_id[0],
            'prev_artists': prev_artists,
        }
        # Please comment this out if you want to keep the voting buttons up.
        sns.publish(
            TopicArn=os.environ['EVALUATE_VOTES_SNS_ARN'],
            Message=json.dumps({'default': json.dumps(sns_event)}),
            MessageStructure='json'
        )

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
        get_channel(event)
        log.info(event)
        store_vote(event)
        retrieve_votes(event)
        update_message(event)
        log.info(response)
    except Exception as e:
        log.error(json.dumps({"message": str(e)}))
    finally:
        return response
