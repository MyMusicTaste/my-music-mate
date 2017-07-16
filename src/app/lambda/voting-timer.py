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


def update_message(event, is_light_on, sleep_duration):
    retrieve_votes(event)
    print('!!! UPDATE MESSAGE !!!')
    message = event['message']
    text = message['text']
    # if '...' in text:
    #     text = text[:-2]
    # else:
    #     text += '.'

    text = ''

    if int(sleep_duration) > 0:
        text += 'Please select one that you are most interested in within '

        minutes = int(sleep_duration / 60)
        seconds = int(sleep_duration - minutes * 60)

        if minutes > 0:
            text += str(minutes) + ' minute(s) '
        if seconds > 0:
            text += str(seconds) + ' second(s).'
    else:
        text += 'Voting has completed. Please wait for a moment while I am collecting the result.'

    if is_light_on is True:
        message['attachments'][0]['color'] = os.environ['BLINK_ON_COLOR']
    else:
        message['attachments'][0]['color'] = os.environ['BLINK_OFF_COLOR']

    if len(message['attachments']) > 0:
        visited_concerts = {}
        for vote in event['votes']:
            if vote['event_id'] not in visited_concerts:
                visited_concerts[vote['event_id']] = 1
            else:
                visited_concerts[vote['event_id']] += 1

        for action in message['attachments'][0]['actions']:
            found = False
            for key in visited_concerts:
                if action['value'] == key:
                    found = True
                    action['text'] = '[' + str(visited_concerts[key]) + '] ' + action['name']
            if found is False:
                action['text'] = '[0] ' + action['name']

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
    # end = int(time.time())

    # return end - start


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
        accumulated_duration = 0
        function_timeout = int(os.environ['VOTING_TIMER_INTERNAL_TIMEOUT'])
        blinking_interval = int(os.environ['VOTING_BLINKING_INTERVAL'])
        extension_timeout = int(os.environ['VOTING_EXTENSION_TIMEOUT'])
        is_light_on = True

        retrieve_intents(event)
        vote_ts = event['intents']['vote_ts']

        # Sleep with blinking animation

        prev_time = time.time()
        while sleep_duration > extension_timeout and accumulated_duration < function_timeout:
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
            print('!!! HISTORY RESPONSE !!!')
            print(response)
            if 'ok' in response and response['ok'] is True:
                if len(response['messages']) == 1:
                    event['message'] = response['messages'][0]
                    print('!!! RETERIVED BUTTON MESSAGE !!!')
                    print(event['message'])
                    update_message(event, is_light_on, sleep_duration)
            # Update prev_time
            prev_time = time.time()

        retrieve_intents(event)
        event['intents']['timeout'] = str(int(sleep_duration))
        store_intents(event)

        if sleep_duration > extension_timeout:
            print('!!! CALL NEW LAMBDA FUNCTION TO KEEP THE TIMER GOES ON !!!')
            # event['intents']['timeout'] = int(sleep_duration)
            # store_intents(event)
            sns_event = {
                'slack': {
                    'team_id': event['slack']['team_id'],
                    'channel_id': event['slack']['channel_id'],
                    'api_token': event['slack']['api_token'],
                    'bot_token': event['slack']['bot_token']
                },
                'timeout': int(sleep_duration)
            }

            sns.publish(
                TopicArn=os.environ['VOTING_TIMER_SNS_ARN'],
                Message=json.dumps({'default': json.dumps(sns_event)}),
                MessageStructure='json'
            )

        elif event['intents']['current_intent'] != 'AskExtend':
            event['intents']['current_intent'] = 'AskExtend'
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
            print('!!! MISSING VOTES !!!')
            log.info(sns_event)
            sns.publish(
                TopicArn=os.environ['DISPATCH_ACTIONS_SNS_ARN'],
                Message=json.dumps({'default': json.dumps(sns_event)}),
                MessageStructure='json'
            )

            prev_time = time.time()
            prev_timeout = event['intents']['timeout']
            print(prev_timeout)
            while sleep_duration > 0 and int(prev_timeout) >= int(event['intents']['timeout']):
                print('!!! VOTING TS !!!')
                vote_ts = event['intents']['vote_ts']
                print(vote_ts)
                print('!!! REMAINING TIME !!!')
                print(sleep_duration)
                print(prev_timeout)
                print(event['intents']['timeout'])

                time.sleep(blinking_interval)

                now_time = time.time()
                sleep_duration -= (now_time - prev_time)
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
                retrieve_intents(event)
                print('!!! REMAINING TIME 2 !!!')
                print(sleep_duration)
                print(prev_timeout)
                print(event['intents']['timeout'])
                # Update prev_time
                prev_time = time.time()

            retrieve_intents(event)
            print('!!! FINISHING VOTING PROCESS')
            print(sleep_duration)
            print(event['intents']['current_intent'])
            if sleep_duration <= 0 and event['intents']['current_intent'] == 'AskExtend':
                print('!!! WAITING IS DONE !!!')
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



            # sns.publish(
            #     TopicArn=os.environ['FINISH_VOTING_SNS_ARN'],
            #     Message=json.dumps({'default': json.dumps(event)}),
            #     MessageStructure='json'
            # )
        store_intents(event)

    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
    finally:
        log.info(response)
        return response
