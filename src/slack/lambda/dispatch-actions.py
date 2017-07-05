# Created by jongwonkim on 11/06/2017.

import os
import logging
import boto3
import json
from src.lex.runtime import LexRunTime

log = logging.getLogger()
log.setLevel(logging.DEBUG)
lex = LexRunTime(os.environ['LEX_NAME'], os.environ['LEX_ALIAS'])
sns = boto3.client('sns')


def talk_with_lex(event):
    event['lex'] = lex.post_message(
        team_id=event['team']['team_id'],
        channel_id=event['slack']['event']['channel'],
        api_token=event['team']['access_token'],
        bot_token=event['team']['bot']['bot_access_token'],
        caller_id=event['slack']['event']['user'],
        message=event['slack']['event']['text']
    )


def publish_to_sns(event):
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
