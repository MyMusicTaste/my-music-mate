# Created by jongwonkim on 12/07/2017.


import os
import logging
import boto3
import json
from src.lex.runtime import LexRunTime
import time
from src.dynamodb.intents import DbIntents
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)
lex = LexRunTime(os.environ['LEX_NAME'], os.environ['LEX_ALIAS'])
sns = boto3.client('sns')
db_intents = DbIntents(os.environ['INTENTS_TABLE'])


def update_message(event, is_light_on, sleep_duration):
    print('!!! UPDATE MESSAGE !!!')
    message = event['message']
    text = message['text']
    # if '...' in text:
    #     text = text[:-2]
    # else:
    #     text += '.'

    text = 'Please select one that you are most interested in. The voting will end within'

    minutes = int(sleep_duration / 60)
    seconds = int(sleep_duration - minutes * 60)

    if minutes > 0:
        text += str(minutes) + ' minute(s) '
    if seconds > 0:
        text += str(seconds) + ' second(s).'

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
    # start = int(time.time())
    sns.publish(
        TopicArn=os.environ['UPDATE_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


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


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    try:
        retrieve_intents(event)
        sleep_duration = int(event['intents']['timeout'])
        accumulated_duration = 0
        function_timeout = int(os.environ['VOTING_TIMER_INTERNAL_TIMEOUT'])
        blinking_interval = int(os.environ['VOTING_BLINKING_INTERVAL'])
        is_light_on = True

        vote_ts = event['intents']['vote_ts']

        # Sleep with blinking animation

        prev_time = time.time()
        while sleep_duration > 0 and accumulated_duration < function_timeout:
            print('!!! REMAINING TIME !!!')
            print(sleep_duration)

            time.sleep(blinking_interval)

            now_time = time.time()
            sleep_duration -= (now_time - prev_time)
            accumulated_duration += (now_time - prev_time)
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
            url = 'https://slack.com/api/channels.history?' + urlencode(params)
            response = requests.get(url).json()
            if 'ok' in response and response['ok'] is True:
                if len(response['messages']) == 1:
                    event['message'] = response['messages'][0]
                    print('!!! RETERIVED BUTTON MESSAGE !!!')
                    print(event['message'])
                    update_message(event, is_light_on, sleep_duration)
            # Update prev_time
            prev_time = time.time()

        retrieve_intents(event)
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
        else:
            print('!!! CALL NEW LAMBDA FUNCTION TO KEEP THE TIMER GOES ON !!!')
            event['intents']['timeout'] = int(sleep_duration)

            sns_event = {
                'slack': {
                    'team_id': event['slack']['team_id'],
                    'channel_id': event['slack']['channel_id'],
                    'api_token': event['slack']['api_token'],
                    'bot_token': event['slack']['bot_token']
                },
                'timeout': int(event['intents']['timeout'])
            }

            sns.publish(
                TopicArn=os.environ['VOTING_TIMER_SNS_ARN'],
                Message=json.dumps({'default': json.dumps(sns_event)}),
                MessageStructure='json'
            )
        store_intents(event)


        # time.sleep(int(os.environ['VOTING_EXTENSION_TIMEOUT']))
        #
        # retrieve_intents(event)
        # log.info(event)
        # print('!!! WAITING IS DONE !!!')
        # if event['intents']['timeout'] == '0' and event['intents']['current_intent'] == 'AskExtend':
        #     sns_event = {
        #         'team': {
        #             'team_id': event['slack']['team_id'],
        #             'access_token': event['slack']['api_token'],
        #             'bot': {
        #                 'bot_access_token': event['slack']['bot_token']
        #             }
        #         },
        #         'slack': {
        #             'event': {
        #                 'channel': event['slack']['channel_id'],
        #                 'user': event['intents']['host_id'],
        #                 'text': 'no'
        #             }
        #         }
        #     }
        #     log.info(sns_event)
        #     sns.publish(
        #         TopicArn=os.environ['DISPATCH_ACTIONS_SNS_ARN'],
        #         Message=json.dumps({'default': json.dumps(sns_event)}),
        #         MessageStructure='json'
        #     )

    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
