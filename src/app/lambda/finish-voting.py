# Created by jongwonkim on 12/07/2017.


import os
import logging
import boto3
import json
from src.lex.runtime import LexRunTime
import time
from src.dynamodb.intents import DbIntents

log = logging.getLogger()
log.setLevel(logging.DEBUG)
lex = LexRunTime(os.environ['LEX_NAME'], os.environ['LEX_ALIAS'])
sns = boto3.client('sns')
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


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


# def store_intents(event):
#     return db_intents.store_intents(
#         keys={
#             'team_id': event['slack']['team_id'],
#             'channel_id': event['slack']['channel_id']
#         },
#         attributes=event['intents']
#     )


def retrieve_intents(event):
    # if 'sessionAttributes' not in event:
    #     raise Exception('Required keys: `team_id` and `channel_id` are not provided.')
    event['intents'] = db_intents.retrieve_intents(
        event['slack']['team_id'],
        event['slack']['channel_id']
    )


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    try:
        time.sleep(int(os.environ['VOTING_EXTENSION_TIMEOUT']))
        
        retrieve_intents(event)
        log.info(event)
        print('!!! WAITING IS DONE !!!')
        if event['intents']['timeout'] == '0' and event['intents']['current_intent'] == 'AskExtend':
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
                        'text': 'no'
                    }
                }
            }
            log.info(sns_event)
            sns.publish(
                TopicArn=os.environ['DISPATCH_ACTIONS_SNS_ARN'],
                Message=json.dumps({'default': json.dumps(sns_event)}),
                MessageStructure='json'
            )

    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
