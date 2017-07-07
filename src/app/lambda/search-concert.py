# Created by jongwonkim on 07/07/2017.


import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests
import random
import time

log = logging.getLogger()
log.setLevel(logging.DEBUG)


def add_taste(event, taste_name, taste_type, interest):
    if taste_name.lower() not in event['intents']['tastes']:
        event['intents']['tastes'][taste_name.lower()] = {
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
                add_taste(event, album['artist']['name'], 'atist', genre)
            else:
                break;


def add_artist_tastes(event):
    log.info('!!! ADD ARTISTS TO TASTES !!!')
    log.info(event)
    artists = event['intents']['artists']
    for artist in artists:
        add_taste(event, artist, 'atist', artist)


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
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
    finally:
        return response
