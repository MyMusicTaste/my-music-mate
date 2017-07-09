# Created by jongwonkim on 09/07/2017.


import os
import logging
import json
import boto3
from botocore.exceptions import ClientError
from src.dynamodb.intents import DbIntents
from src.dynamodb.concerts import DbConcerts
import requests
from requests.exceptions import HTTPError
import random
import time
from urllib.parse import quote_plus

from urllib.request import urlopen


log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
db_concerts = DbConcerts(os.environ['CONCERTS_TABLE'])
sns = boto3.client('sns')


STATUS_REVOTE = 'R'
STATUS_WINNER = 'W'
STATUS_NOPE = 'N'

def count_votes(event):
    visited_concerts = {}
    for vote in event['votes']:
        if vote['event_id'] not in visited_concerts:
            visited_concerts[vote['event_id']] = 1
        else:
            visited_concerts[vote['event_id']] += 1

    print(visited_concerts)

    vote_result = STATUS_REVOTE     # N: I don't like any of these, W: Instant winner, R: Re-vote
    vote_winner = None
    new_queue = []
    for key in visited_concerts:
        percentage = visited_concerts[key] / int(os.environ['CONCERT_VOTE_OPTIONS_MAX'])
        if key == '0' and percentage > 0.4:  # I don't like any of these options
            vote_result = STATUS_NOPE
            break
        elif percentage > 0.65:
            vote_result = STATUS_WINNER
            vote_winner = key
            break

    if vote_result == 'R':
        for key in visited_concerts:
            percentage = visited_concerts[key] / int(os.environ['CONCERT_VOTE_OPTIONS_MAX'])
            if percentage > 0.3 and key != '0':
                new_queue.append(key)
    event['result'] = {
        'status': vote_result,
        'winner': vote_winner,
        'queue': new_queue
    }


def show_ticket_link(event):
    print('!!! SHOW TICKET LINK!!!')
    db_response = db_concerts.get_concert(event['channel_id'], event['result']['winner'])
    ticket_link = None
    ticket_image = None
    ticket_thumb = None
    if 'ticket_url' in db_response:
        ticket_link = db_response['ticket_url']
        ticket_image = db_response['artists'][0]['image_url']
        ticket_thumb = db_response['artists'][0]['thumb_url']
    print(ticket_link)
    if ticket_link is not None:
        # print(response.history)
        text = 'Here is a ticket link!'
        attachments = [
            {
                'text': ticket_link,
                # 'image_url': ticket_image,
                # 'thumb_url': ticket_thumb
            }
        ]
        sns_event = {
            'token': event['token'],
            'channel': event['channel_id'],
            'text': text,
            'attachments': attachments
        }
        log.info('!!! SNS EVENT !!!')
        log.info(sns_event)
        print('!!! SNS EVENT !!!')
        print(sns_event)
        print('!!! ARN ADDRRESS !!!')
        print(os.environ['POST_MESSAGE_SNS_ARN'])
        return sns.publish(
            TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
            Message=json.dumps({'default': json.dumps(sns_event)}),
            MessageStructure='json'
        )


def execute_second_vote(event):
    print('!!! EXECUTE SECOND VOTE !!!')



def bring_new_concert_queue(event):
    print('!!! BRING NEW CONCERT QUEUE !!!')

def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200
    }
    # try:
    log.info(event)
    count_votes(event)
    if event['result']['status'] == STATUS_WINNER:
        show_ticket_link(event)
    elif event['result']['status'] == STATUS_REVOTE:
        execute_second_vote(event)
    elif event['result']['status'] == STATUS_NOPE:
        bring_new_concert_queue(event)

    log.info(response)
    # except Exception as e:
    #     response = {
    #         "statusCode": 400,
    #         "body": json.dumps({"message": str(e)})
    #     }
    #     log.error(response)
    # finally:
    #     return response
