# Created by jongwonkim on 11/07/2017.


import os
import logging
import boto3
import json
from src.lex.runtime import LexRunTime
import time
from src.dynamodb.votes import DbVotes
from src.dynamodb.intents import DbIntents
from urllib.parse import urlencode
import requests
import random

log = logging.getLogger()
log.setLevel(logging.DEBUG)
lex = LexRunTime(os.environ['LEX_NAME'], os.environ['LEX_ALIAS'])
sns = boto3.client('sns')
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
db_votes = DbVotes(os.environ['VOTES_TABLE'])


def update_message(event, is_light_on):
    print('!!! UPDATE MESSAGE !!!')
    message = event['message']
    text = message['text']
    if '...' in text:
        text = text[:-2]
    else:
        text += '.'

    if is_light_on is True:
        message['attachments'][0]['color'] = os.environ['BLINK_ON_COLOR']
    else:
        message['attachments'][0]['color'] = os.environ['BLINK_OFF_COLOR']

    sns_event = {
        'token': event['slack']['bot_token'],
        'channel': event['slack']['channel_id'],
        'text': text,
        'attachments': message['attachments'],
        'ts': message['ts'],
        'as_user': True
    }
    print('!!! SNS EVENT !!!')
    print(sns_event)
    start = int(time.time())
    sns.publish(
        TopicArn=os.environ['UPDATE_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )
    end = int(time.time())

    return end - start


# def talk_with_lex(event):
#     event['lex'] = lex.post_message(
#         team_id=event['team']['team_id'],
#         channel_id=event['slack']['event']['channel'],
#         api_token=event['team']['access_token'],
#         bot_token=event['team']['bot']['bot_access_token'],
#         caller_id=event['slack']['event']['user'],
#         message=event['slack']['event']['text']
#     )
#
#
# def publish_to_sns(event):
#     sns_event = {
#         'token': event['lex']['sessionAttributes']['bot_token'],
#         'channel': event['lex']['sessionAttributes']['channel_id'],
#         'text': event['lex']['message']
#     }
#     return sns.publish(
#         TopicArn=os.environ['SNS_ARN'],
#         Message=json.dumps({'default': json.dumps(sns_event)}),
#         MessageStructure='json'
#     )

# def post_message_to_slack(event):
#     params = {
#         "token": event['lex']['sessionAttributes']['bot_token'],
#         "channel": event['lex']['sessionAttributes']['channel_id'],
#         "text": event['lex']['message']
#     }
#     url = 'https://slack.com/api/chat.postMessage?' + urlencode(params)
#     response = requests.get(url).json()
#     if 'ok' in response and response['ok'] is True:
#         return
#     raise Exception('Failed to post a message to a Slack channel!')


def store_intents(event):
    return db_intents.store_intents(
        keys={
            'team_id': event['slack']['team_id'],
            'channel_id': event['slack']['channel_id']
        },
        attributes=event['intents']
    )


def retrieve_intents(event):
    # if 'sessionAttributes' not in event:
    #     raise Exception('Required keys: `team_id` and `channel_id` are not provided.')
    event['intents'] = db_intents.retrieve_intents(
        event['slack']['team_id'],
        event['slack']['channel_id']
    )


def retrieve_votes(event):
    db_response = db_votes.fetch_votes(event['slack']['channel_id'])
    print('!!! db_response !!!')
    print(db_response)
    event['votes'] = db_response


def get_channel(event):
    params = {
        'token': event['slack']['api_token'],
        'channel': event['slack']['channel_id']
    }
    url = 'https://slack.com/api/channels.info?' + urlencode(params)
    response = requests.get(url).json()
    print('!!! RESPONSE !!!')
    print(response)
    if 'ok' in response and response['ok'] is True:
        event['channel'] = response['channel']
        return
    raise Exception('Failed to get a Slack channel info!')


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    try:
        sleep_duration = int(event['timeout'])
        blinking_interval = int(os.environ['VOTING_BLINKING_INTERVAL'])
        is_light_on = True

        retrieve_intents(event)
        vote_ts = event['intents']['vote_ts']

        # Sleep with blinking animation
        while sleep_duration > 0:

            print('!!! REMAINING TIME !!!')
            print(sleep_duration)

            time.sleep(blinking_interval)
            sleep_duration -= blinking_interval
            if is_light_on is True:
                is_light_on = False
            else:
                is_light_on = True

            params = {
                'token': event['slack']['api_token'],
                'channel': event['slack']['channel_id'],
                'count': 1,
                'inclusive': True,
                'latest': vote_ts,
                'oldest': vote_ts
            }
            start = int(time.time())
            url = 'https://slack.com/api/channels.history?' + urlencode(params)
            response = requests.get(url).json()
            end = int(time.time())

            sleep_duration -= (end - start)
            if 'ok' in response and response['ok'] is True:
                if len(response['messages']) == 1:
                    event['message'] = response['messages'][0]
                    print('!!! RETERIVED BUTTON MESSAGE !!!')
                    print(event['message'])
                    sleep_duration -= update_message(event, is_light_on)



        # Turn off the light.
        params = {
            'token': event['slack']['api_token'],
            'channel': event['slack']['channel_id'],
            'count': 1,
            'inclusive': True,
            'latest': vote_ts,
            'oldest': vote_ts
        }
        url = 'https://slack.com/api/channels.history?' + urlencode(params)
        response = requests.get(url).json()
        if 'ok' in response and response['ok'] is True:
            if len(response['messages']) == 1:
                event['message'] = response['messages'][0]
                print('!!! RETERIVED BUTTON MESSAGE !!!')
                print(event['message'])
                update_message(event, False)

        retrieve_intents(event)
        get_channel(event)
        retrieve_votes(event)
        if len(event['votes']) == (len(event['channel']['members']) - 1):   # Exclude the bot itself from the voting.
            event['intents']['current_intent'] = 'EvaluateVotes'
            text = 'Voting is completed. I will show you the result shortly.'
            callback_id = event['intents']['callback_id'].split('|')
            prev_artists = ''
            if len(callback_id) > 1:
                prev_artists = callback_id[1]

            sns_event = {
                'team_id': event['slack']['team_id'],
                'channel_id': event['slack']['channel_id'],
                'token': event['slack']['bot_token'],
                'api_token': event['slack']['api_token'],
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
        else:
            sns_event = {
                'team': {
                    'team_id': event['slack']['team_id'],
                    'access_token': event['slack']['api_token'],
                    'bot': {
                        'bot_access_token': event['slack']['bot_token']
                    }
                },
                'slack': {
                    'event': {
                        'channel': event['slack']['channel_id'],
                        'user': event['intents']['host_id'],
                        'text': 'THIS ASK EXTEND INTENT SHOULD NOT BE INVOKED BY ANY UTTERANCES'
                    }
                }
            }
            log.info(sns_event)
            sns.publish(
                TopicArn=os.environ['DISPATCH_ACTIONS_SNS_ARN'],
                Message=json.dumps({'default': json.dumps(sns_event)}),
                MessageStructure='json'
            )

            sns.publish(
                TopicArn=os.environ['FINISH_VOTING_SNS_ARN'],
                Message=json.dumps({'default': json.dumps(event)}),
                MessageStructure='json'
            )

        event['intents']['timeout'] = '0'
        store_intents(event)

    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
