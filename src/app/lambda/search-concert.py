# Created by jongwonkim on 07/07/2017.


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


log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
db_concerts = DbConcerts(os.environ['CONCERTS_TABLE'])
sns = boto3.client('sns')


def mark_queued_concerts(queued):
    for concert in queued:
        db_response = db_concerts.add_concert({
            'team_id': concert['team_id'],
            'channel_id': concert['channel_id'],
            'artists': concert['artists'],
            'event_id': concert['event_id'],
            'event_name': concert['event_name'],
            'event_date': concert['event_date'],
            'event_venue': concert['event_venue'],
            'ticket_url': concert['ticket_url'],
            'interest': concert['interest'],
            'queued': True
        })
        log.info('!!! CONCERT DB UPDATE RESPONSE !!!')
        log.info(db_response)
        print('!!! CONCERT DB UPDATE RESPONSE !!!')
        print(db_response)


def publish_voting_ui(event, queued):
    text = 'Please select one that you are most interested in.'
    attachments = [
        {
            'fallback': 'You are unable to vote',
            'callback_id': event['sessionAttributes']['channel_id'],
            'color': '#3AA3E3',
            'attachment_type': 'default',
            'actions': []
        }
    ]
    for i, concert in enumerate(queued):
        artists = []
        print('!!! CONCERT INDIVIDUAL !!!')
        print(concert)
        for artist in concert['artists']:
            artists.append(artist['name'])

        attachments[0]['actions'].append({
            'name': concert['event_name'],
            'text': concert['event_name'],
            'type': 'button',
            'value': concert['event_id']
        })

    attachments[0]['actions'].append({
        'name': 'none',
        'text': 'Other options?',
        'type': 'button',
        'style': 'danger',
        'value': '0'
    })

    log.info('!!! ATTACHMENTS !!!')
    log.info(attachments)
    print('!!! ATTACHMENTS !!!')
    print(attachments)
    sns_event = {
        'token': event['sessionAttributes']['bot_token'],
        'channel': event['sessionAttributes']['channel_id'],
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


def publish_concert_list(event, queued):
    # if len(queued) == 0:
    #     text = 'Sorry, I couldn\'t find any concert you might interested in.'
    # elif len(queued) > 1:
    #     text = 'Here are {} concerts that you guys might interested in.'.format(len(queued))
    # else:
    #     text = 'Hmm, I only found one option. Are you interested in?'
    print('!!! QUEUED !!!')
    print(queued)
    attachments = []
    for i, concert in enumerate(queued):
        artists = []
        print('!!! CONCERT INDIVIDUAL !!!')
        print(concert)
        for artist in concert['artists']:
            artists.append(artist['name'])

        pretext = ''
        order = ''
        if i == 0:
            if len(queued) == i + 1:
                order = ''
            else:
                order = 'first'
        if i == 1:
            if len(queued) == i + 1:
                order = 'last'
            else:
                order = 'second'
        elif i == 2:
            if len(queued) == i + 1:
                order = 'last'
            else:
                order = 'last'

        pretext += 'Here is the {} option. I chose this because you are interested in {}.'.format(
            order, concert['interest'])

        attachments.append({
            'pretext': pretext,
            'title': concert['event_name'],
            'author_name': ', '.join(artists),
            'author_icon': concert['artists'][0]['thumb_url'],
            'fields': [
                {
                    'title': 'Concert Date:',
                    'value': concert['event_date'],
                    'short': True
                },
                {
                    'title': 'Concert Location:',
                    'value': concert['event_venue']['name'] + ', ' + concert['event_venue']['city'] + ', ' +
                             concert['event_venue']['region'],
                    'short': True
                },
                # {
                #     'title': 'Lineup:',
                #     'value': ', '.join(artists)
                # }
            ]
        })

    log.info('!!! ATTACHMENTS !!!')
    log.info(attachments)
    print('!!! ATTACHMENTS !!!')
    print(attachments)
    sns_event = {
        'token': event['sessionAttributes']['bot_token'],
        'channel': event['sessionAttributes']['channel_id'],
        'text': '',
        'attachments': attachments
    }
    log.info('!!! SNS EVENT !!!')
    log.info(sns_event)
    print('!!! SNS EVENT !!!')
    print(sns_event)
    print('!!! ARN ADDRRESS !!!')
    print (os.environ['POST_MESSAGE_SNS_ARN'])
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
        # TODO When we shuffled the list, there is lot of chance that we pick artists who don't have concert schedules
        random.shuffle(top_albums)
        log.info('!!! SHUFFLED TOP ALBUMS !!!')
        log.info(top_albums)
        for i, album in enumerate(top_albums):
            if i < int(os.environ['GENRE_TO_ARTIST_MAX']):
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
            try:
                print('!!! API ADDRESS !!!')
                print(os.environ['BIT_CONCERT_SEARCH_BY_ARTISTS_API'].format(
                        taste['taste_name'],
                        event['intents']['city'],
                        os.environ['CONCERT_SEARCH_RADIUS']))
                concerts = requests.get(
                    os.environ['BIT_CONCERT_SEARCH_BY_ARTISTS_API'].format(
                        taste['taste_name'],
                        event['intents']['city'],
                        os.environ['CONCERT_SEARCH_RADIUS']
                )).json()
                print('!!! api_response !!!')
                print(concerts)
                for concert in concerts:
                    if concert['ticket_url'] is not None:
                        artists = []
                        if 'artists' in concert:
                            for artist in concert['artists']:
                                artists.append({
                                    'name': artist['name'],
                                    'thumb_url': artist['thumb_url'],
                                    'image_url': artist['image_url']
                                })

                        if 'venue' in concert:
                            print('!!! CONVERT VENUE !!!')
                            print(concert['venue'])
                            concert['venue']['latitude'] = str(concert['venue']['latitude'])
                            concert['venue']['longitude'] = str(concert['venue']['longitude'])

                        try:
                            # Store concert data into a db table for tracking voting results.
                            db_response = db_concerts.add_concert({
                                'team_id': event['sessionAttributes']['channel_id'],
                                'channel_id': event['sessionAttributes']['channel_id'],
                                'artists': artists,
                                'event_id': str(concert['id']),
                                'event_name': concert['title'],
                                'event_date': concert['formatted_datetime'],
                                'event_venue': concert['venue'],
                                'ticket_url': concert['ticket_url'],
                                'interest': taste['interest'],
                                'queued': False
                            })
                            log.info('!!! CONCERT DB ADD RESPONSE !!!')
                            log.info(db_response)
                            print('!!! CONCERT DB ADD RESPONSE !!!')
                            print(db_response)
                        except ClientError:
                            log.error('Conditional Check Failed Exception during concert search')
            except Exception as e:
                log.error('Error coming from BIT API')
                print('Error coming from BIT API')
                log.error(str(e))
                print(str(e))


def show_results(event):
    concerts = db_concerts.fetch_concerts(event['sessionAttributes']['channel_id'])
    print('!!! SHOW CONCERT RESULTS !!!')
    print(concerts)
    log.info('!!! SHOW CONCERT RESULTS !!!')
    log.info(concerts)
    artist_visited = []
    concerts_queued = []

    for concert in concerts:
        if len(concerts_queued) < int(os.environ['CONCERT_VOTE_OPTIONS_MAX']):
            print('!!! artist_visited !!!')
            print(artist_visited)
            print('!!! concerts_queued !!!')
            print(concerts_queued)
            artists = concert['artists']
            need_to_be_queued = True
            for artist in artists:
                if artist['name'] not in artist_visited:
                    artist_visited.append(artist['name'])
                else:
                    need_to_be_queued = False
            if need_to_be_queued:
                concerts_queued.append(concert)
        else:
            break
    mark_queued_concerts(concerts_queued)
    publish_concert_list(event, concerts_queued)
    time.sleep(2.5)
    publish_voting_ui(event, concerts_queued)


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
