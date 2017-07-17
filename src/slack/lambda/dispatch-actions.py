# Created by jongwonkim on 11/06/2017.

import os
import logging
import boto3
import json
from src.lex.runtime import LexRunTime
from src.dynamodb.intents import DbIntents
import time

log = logging.getLogger()
log.setLevel(logging.DEBUG)
lex = LexRunTime(os.environ['LEX_NAME'], os.environ['LEX_ALIAS'])
sns = boto3.client('sns')
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


def store_intents(event):
    return db_intents.store_intents(
        keys={
            'team_id': event['team']['team_id'],
            'channel_id': event['slack']['event']['channel']
        },
        attributes=event['intents']
    )


def retrieve_intents(event):
    event['intents'] = db_intents.retrieve_intents(
        event['team']['team_id'],
        event['slack']['event']['channel']
    )


def talk_with_lex(event):
    retrieve_intents(event)
    # Block the lex invoke during voting.
    if event['intents']['current_intent'] != 'VotingConcert' and event['intents']['current_intent'] != 'EvaluateVotes':
        if 'callback_id' not in event['slack']['event']:
            event['slack']['event']['callback_id'] = ''

        lex_identifier = event['intents']['lex_identifier']
        if lex_identifier is None:
            lex_identifier = event['team']['team_id'] + event['slack']['event']['channel'] + event['slack']['event']['user'] + str(int(time.time()))
            event['intents']['lex_identifier'] = lex_identifier
            store_intents(event)

        print('!!! LEX IDENTIFIER !!!')
        print(lex_identifier)
        print(event['intents'])

        event['lex'] = lex.post_message(
            lex_identifier=lex_identifier,
            team_id=event['team']['team_id'],
            channel_id=event['slack']['event']['channel'],
            api_token=event['team']['access_token'],
            bot_token=event['team']['bot']['bot_access_token'],
            caller_id=event['slack']['event']['user'],
            callback_id=event['slack']['event']['callback_id'],
            message=event['slack']['event']['text']
        )


def publish_to_sns(event):
    if 'lex' in event:
        sns_event = {
            'token': event['lex']['sessionAttributes']['bot_token'],
            'channel': event['lex']['sessionAttributes']['channel_id'],
            'text': event['lex']['message']
        }
        return sns.publish(
            TopicArn=os.environ['SNS_ARN'],
            Message=json.dumps({'default': json.dumps(sns_event)}),
            MessageStructure='json'
        )

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


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    try:
        talk_with_lex(event)
        publish_to_sns(event)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
