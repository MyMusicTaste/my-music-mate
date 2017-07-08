# Created by jongwonkim on 07/07/2017.


import os
import logging
import json
import boto3
from botocore.exceptions import ClientError
from src.dynamodb.intents import DbIntents
from src.dynamodb.concerts import DbConcerts
import requests
import random
sns = boto3.client('sns')


log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
db_concerts = DbConcerts(os.environ['CONCERTS_TABLE'])


def publish_to_sns(event, message):
    sns_event = {
        'token': event['sessionAttributes']['bot_token'],
        'channel': event['sessionAttributes']['channel_id'],
        'text': message
    }
    return sns.publish(
        TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def store_intents(event):
    return db_intents.store_intents(
        keys={
            'team_id': event['sessionAttributes']['team_id'],
            'channel_id': event['sessionAttributes']['channel_id']
        },
        attributes=event['intents']
    )


def add_taste(event, taste_name, taste_type, interest):
    if taste_name.lower() not in event['intents']['tastes']:
        event['intents']['tastes'][taste_name.lower()] = {
            'taste_name': taste_name.lower(),
            'display_name': taste_name,
            'taste_type': taste_type,
            'interest': interest
        }
    log.info('!!! ADD TASTE !!!')
    log.info(event)


def add_genre_tastes(event):
    # Take each Genre from the Tastes table and use the lastfm API to obtain a random list of related artists (limit 3)
    log.info('!!! ADD GENRES TO TASTES !!!')
    log.info(event)
    genres = event['intents']['genres']
    for genre in genres:
        api_response = requests.get(os.environ['LASTFM_TOP_URL'].format(genre))
        log.info('!!! API RESPONSE !!!')
        log.info(api_response)
        top_albums = json.loads(api_response.text)['albums']['album']
        log.info('!!! TOP ALBUMS !!!')
        log.info(top_albums)
        random.shuffle(top_albums)
        log.info('!!! SUFFLED TOP ALBUMS !!!')
        log.info(top_albums)
        for i, album in enumerate(top_albums):
            if i < int(os.environ['TOP_ALBUMS_MAX']):
                add_taste(event, album['artist']['name'], 'artist', genre)
            else:
                break


def add_artist_tastes(event):
    log.info('!!! ADD ARTISTS TO TASTES !!!')
    log.info(event)
    artists = event['intents']['artists']
    for artist in artists:
        add_taste(event, artist, 'artist', artist)


def search_concerts(event):
    log.info('!!! SEARCH CONCERTS !!!')
    for key in event['intents']['tastes']:
        taste = event['intents']['tastes'][key]
        log.info('!!! CONCERT ITEM !!!')
        log.info(taste)
        if taste['taste_type'] == 'artist':
            log.info('!!! API ADDRESS !!!')
            log.info(os.environ['BIT_CONCERT_SEARCH_BY_ARTISTS_API'].format(
                    taste['taste_name'],
                    event['intents']['city'],
                    os.environ['CONCERT_SEARCH_RADIUS']))
            api_response = requests.get(
                os.environ['BIT_CONCERT_SEARCH_BY_ARTISTS_API'].format(
                    taste['taste_name'],
                    event['intents']['city'],
                    os.environ['CONCERT_SEARCH_RADIUS'])
            )
            concerts = json.loads(api_response.text)
            log.info('!!! CONCERT SEARCH API RESPONSE !!!')
            log.info(concerts)
            for concert in concerts:
                if concert['ticket_url'] is not None:
                    try:
                        # Store concert data into a db table for tracking voting results.
                        db_response = db_concerts.add_concert({
                            'team_id': event['sessionAttributes']['channel_id'],
                            'channel_id': event['sessionAttributes']['channel_id'],
                            'artist': concert['artists'][0]['name'],
                            'event_id': str(concert['id']),
                            'event_name': concert['title'],
                            'event_date': concert['formatted_datetime'],
                            'ticket_url': concert['ticket_url'],
                            'interest': taste['interest']
                        })
                        log.info('!!! CONCERT DB ADD RESPONSE !!!')
                        log.info(db_response)
                    except ClientError:
                        log.error('Conditional Check Failed Exception during concert search')


def show_results(event):
    concerts = db_concerts.fetch_concerts(event['sessionAttributes']['channel_id'])
    log.info('!!! SHOW CONCERT RESULTS !!!')
    log.info(concerts)
    # TODO Need to show the list to Slack channel
    # publish_to_sns(event, message)


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": 'message has been sent successfully.'})
    }
    try:
        log.info(response)
        add_artist_tastes(event)
        add_genre_tastes(event)
        store_intents(event)
        search_concerts(event)
        show_results(event)
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
    finally:
        return response
