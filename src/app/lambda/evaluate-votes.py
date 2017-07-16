# Created by jongwonkim on 09/07/2017.


import os
import logging
import json
import boto3
from botocore.exceptions import ClientError
from src.dynamodb.votes import DbVotes
from src.dynamodb.concerts import DbConcerts
from src.dynamodb.intents import DbIntents
import requests
from googleapiclient.discovery import build
from requests.exceptions import HTTPError
import random
import time
from urllib.parse import urlencode
import requests
from urllib.parse import quote_plus

from urllib.request import urlopen


log = logging.getLogger()
log.setLevel(logging.DEBUG)
db_votes = DbVotes(os.environ['VOTES_TABLE'])
db_concerts = DbConcerts(os.environ['CONCERTS_TABLE'])
db_intents = DbIntents(os.environ['INTENTS_TABLE'])
sns = boto3.client('sns')



STATUS_REVOTE = 'R'
STATUS_WINNER = 'W'
STATUS_NOPE = 'N'


def update_message(event):
    print('!!! UPDATE MESSAGE !!!')
    message = event['message']
    text = 'Voting has completed. Please wait while I collect the result.'

    message['attachments'][0]['color'] = os.environ['MESSAGE_DEFAULT_COLOR']

    sns_event = {
        'token': event['token'],
        'channel': event['channel_id'],
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


def activate_voting_timer(event, voting_round, artist_visited):
    event['intents']['timeout'] = os.environ['DEFAULT_VOTING_TIMEOUT']
    sns_event = {
        'slack': {
            'team_id': event['team_id'],
            'channel_id': event['channel_id'],
            'api_token': event['api_token'],
            'bot_token': event['token']
        },
        'timeout': os.environ['DEFAULT_VOTING_TIMEOUT']
    }

    return sns.publish(
        TopicArn=os.environ['VOTING_TIMER_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def publish_voting_ui(event, queued, artist_visited):
    event['intents']['callback_id'] = '1|' + ','.join(artist_visited)
    text = 'Please select the concert you are most interested in within '
    sleep_duration = int(os.environ['DEFAULT_VOTING_TIMEOUT'])
    minutes = int(sleep_duration / 60)
    seconds = int(sleep_duration - minutes * 60)

    if minutes > 0:
        if minutes == 1:
            text += str(minutes) + ' minute'
        else:
            text += str(minutes) + ' minutes'
    if seconds > 0:
        if minutes > 0:
            text += ' '
        if seconds == 1:
            text += str(seconds) + ' second'
        else:
            text += str(seconds) + ' seconds'
    text += '.'

    attachments = [
        {
            'fallback': 'You are unable to vote',
            'callback_id': '1|' + ','.join(artist_visited),     # Second round + artist names
            'color': os.environ['BLINK_OFF_COLOR'],
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
            'text': '[0] ' + concert['event_name'],
            'type': 'button',
            'style': 'primary',
            'value': concert['event_id']
        })

    attachments[0]['actions'].append({
        'name': 'Other options?',
        'text': '[0] Other options?',
        'type': 'button',
        'value': '0'
    })

    log.info('!!! ATTACHMENTS !!!')
    log.info(attachments)
    print('!!! ATTACHMENTS !!!')
    print(attachments)
    sns_event = {
        'team': event['team_id'],
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
    sns.publish(
        TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )
    # Activate the voting timer.
    activate_voting_timer(event, 1, artist_visited)


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


def publish_concert_list(event, queued):
    # if len(queued) == 0:
    #     text = 'Sorry, I couldn\'t find any concert you might interested in.'
    # elif len(queued) > 1:
    #     text = 'Here are {} concerts that you guys might interested in.'.format(len(queued))
    # else:
    #     text = 'Hmm, I only found one option. Are you interested in?'
    print('!!! QUEUED !!!')
    print(queued)
    youtube = build(os.environ['YOUTUBE_API_SERVICE_NAME'], os.environ['YOUTUBE_API_VERSION'],
                    developerKey=os.environ['DEVELOPER_KEY'])

    for i, concert in enumerate(queued):
        attachments = []
        artists = []
        print('!!! CONCERT INDIVIDUAL !!!')
        print(concert)
        for artist in concert['artists']:
            artists.append(artist['name'])
        search_response = youtube.search().list(
            q=concert['artists'][0]['name'] + " live concert",
            part="id,snippet",
            type="video",
            maxResults=1
        ).execute()
        result = search_response.get("items", [])
        youtubeurl = "http://youtube.com/watch?v=%s" % result[0]["id"]["videoId"]
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

        #pretext += 'Here is the {} option. I chose this because you are interested in {}.'.format(
        #    order, concert['interest'])

        attachments.append({
            #'pretext': pretext,
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
        time.sleep(.5)
        sns_event = {
            'token': event['token'],
            'channel': event['channel_id'],
            'text': "Here is the {} option. I chose this because of your interest in {}. <{}| >".format(
                order, concert['interest'], youtubeurl),
            'attachments': attachments
        }
        sns.publish(
            TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
            Message=json.dumps({'default': json.dumps(sns_event)}),
            MessageStructure='json'
        )
    # log.info('!!! ATTACHMENTS !!!')
    # log.info(attachments)
    # print('!!! ATTACHMENTS !!!')
    # print(attachments)
    #sns_event = {
    #    'token': event['token'],
    #    'channel': event['channel_id'],
    #    'text': '',
    #    'attachments': attachments
    #}
    #log.info('!!! SNS EVENT !!!')
    #log.info(sns_event)
    #print('!!! SNS EVENT !!!')
    #print(sns_event)
    #print('!!! ARN ADDRRESS !!!')
    #print (os.environ['POST_MESSAGE_SNS_ARN'])
    #return sns.publish(
    #    TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
    #    Message=json.dumps({'default': json.dumps(sns_event)}),
    #    MessageStructure='json'
    #)
    return


def count_votes(event):
    visited_concerts = {}
    total_votes = len(event['votes'])
    if total_votes == 0:
        total_votes = 1 # Force to not dividing with 0
    for vote in event['votes']:
        if vote['event_id'] not in visited_concerts:
            visited_concerts[vote['event_id']] = 1
        else:
            visited_concerts[vote['event_id']] += 1

    print(visited_concerts)

    vote_result = None     # N: I don't like any of these, W: Instant winner, R: Re-vote
    vote_winners = []
    new_queue = []

    if event['round'] != '2':   # First vote.
        print('!!! FIRST VOTE !!!')
        vote_result = STATUS_REVOTE
        for key in visited_concerts:
            percentage = visited_concerts[key] / total_votes
            if key == '0' and percentage > 0.4:  # I don't like any of these options
                vote_result = STATUS_NOPE
                break
            elif percentage > 0.65:
                vote_result = STATUS_WINNER
                vote_winners.append(key)
                break

        if vote_result == STATUS_REVOTE:
            for key in visited_concerts:
                percentage = visited_concerts[key] / total_votes
                if percentage > 0.3 and key != '0':
                    new_queue.append(key)

        if vote_result == STATUS_NOPE:
            for key in visited_concerts:
                percentage = visited_concerts[key] / total_votes
                if percentage > 0.4 and key != '0':
                    new_queue.append(key)

    else:   # Second vote.
        print('!!! SECOND VOTE !!!')
        vote_result = STATUS_NOPE
        for key in visited_concerts:
            percentage = visited_concerts[key] / total_votes
            if percentage >= 0.5 and key != '0':
                vote_result = STATUS_WINNER
                vote_winners.append(key)

    event['result'] = {
        'status': vote_result,
        'winners': vote_winners,
        'queue': new_queue
    }


def show_ticket_link(event):
    print('!!! SHOW TICKET LINK!!!')
    print(event['result']['winners'])

    for winner in event['result']['winners']:
        db_response = db_concerts.get_concert(event['channel_id'], winner)
        ticket_link = None
        ticket_image = None
        ticket_thumb = None
        if 'ticket_url' in db_response:
            ticket_link = db_response['ticket_url']
            ticket_image = db_response['artists'][0]['image_url']
            ticket_thumb = db_response['artists'][0]['thumb_url']
        print('!!! TICKET LINK !!!')
        print(ticket_link)
        if ticket_link is not None:
            artists = []
            for artist in db_response['artists']:
                artists.append(artist['name'])

            # print(response.history)
            text = 'Here is a ticketing site link! \nEnjoy the show with your friends! :balloon: <{}?link={}| >'\
                .format(os.environ['TICKET_PAGE_LINK'], ticket_link)
            attachments = [
                {
                    'title': db_response['event_name'],
                    'author_name': ', '.join(artists),
                    'author_icon': db_response['artists'][0]['thumb_url'],
                    'fields': [
                        {
                            'title': 'Concert Date:',
                            'value': db_response['event_date'],
                            'short': True
                        },
                        {
                            'title': 'Concert Location:',
                            'value': db_response['event_venue']['name'] + ', ' + db_response['event_venue']['city'] + ', ' +
                                     db_response['event_venue']['region'],
                            'short': True
                        }
                    ]
                    # 'image_url': ticket_image,
                    # 'thumb_url': ticket_thumb
                }
            ]
            sns_event = {
                'token': event['token'],
                'channel': event['channel_id'],
                'text': text,
                'attachments': attachments,
                'unfurl_links': True
            }
            log.info('!!! SNS EVENT !!!')
            log.info(sns_event)
            print('!!! SNS EVENT !!!')
            print(sns_event)
            print('!!! ARN ADDRRESS !!!')
            print(os.environ['POST_MESSAGE_SNS_ARN'])
            sns.publish(
                TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
                Message=json.dumps({'default': json.dumps(sns_event)}),
                MessageStructure='json'
            )
    db_concerts.remove_all(event['channel_id'])


def execute_second_vote(event):
    print('!!! EXECUTE SECOND VOTE !!!')
    queued = []
    for concert in event['result']['queue']:
        db_response = db_concerts.get_concert(event['channel_id'], concert)
        if db_response is not None:
            queued.append(db_response)

    print('!!! queued_concerts !!!')
    print(queued)

    # try:
    sns_event = {
        'token': event['token'],
        'channel': event['channel_id'],
        'text': "It looks like there wasn't a clear winner after the previous vote. I've eliminated any unwanted "
                "concerts so please take a look at the remaining choices and vote again."
    }
    sns.publish(
        TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )
    time.sleep(2)
    print('!!! DELETE PREVIOUS VOTES !!!')
    for member in event['members']:
        print(event['channel_id'])
        print(member)
        db_response = db_votes.remove_previous(event['channel_id'], '_' + member)
    # except Exception as e:
    #     log.error('DB ERROR')
    #     print('DB ERROR')
    #     log.error(str(e))
    #     print(str(e))

    event['intents']['callback_id'] = '2'

    text = 'Here are your new voting options.'
    attachments = [
        {
            'fallback': 'You are unable to vote',
            'callback_id': '2', # Second round
            'color': os.environ['BLINK_OFF_COLOR'],
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
            'text': '[0] ' + concert['event_name'],
            'type': 'button',
            'style': 'primary',
            'value': concert['event_id']
        })

    # attachments[0]['actions'].append({
    #     'name': 'none',
    #     'text': 'Other options?',
    #     'type': 'button',
    #     'style': 'danger',
    #     'value': '0'
    # })

    log.info('!!! ATTACHMENTS !!!')
    log.info(attachments)
    print('!!! ATTACHMENTS !!!')
    print(attachments)
    sns_event = {
        'team': event['team_id'],
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
    sns.publish(
        TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )
    # Activate the voting timer.
    activate_voting_timer(event, 2, [])


def bring_new_concert_queue(event):
    print('!!! DELETE PREVIOUS VOTES !!!')
    for member in event['members']:
        print(event['channel_id'])
        print(member)
        db_response = db_votes.remove_previous(event['channel_id'], '_' + member)

    sns_event = {
        'token': event['token'],
        'channel': event['channel_id'],
        'text': "It looks like you guys didn't really like that last group of concerts. Let me see if there were any"
                "more concerts for me to show you."
    }
    sns.publish(
        TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )
    time.sleep(5)
    print('!!! BRING NEW CONCERT QUEUE !!!')
    concerts = db_concerts.fetch_concerts(event['channel_id'])
    print('!!! SHOW CONCERT RESULTS !!!')
    print(concerts)
    log.info('!!! SHOW CONCERT RESULTS !!!')
    log.info(concerts)
    artist_visited = event['prev_artists'].replace('+', ' ').split(',')
    log.info('!!! PREV ARTISTS')
    log.info(artist_visited)
    print('!!! PREV ARTISTS')
    print(artist_visited)
    concerts_queued = []
    for survived_concert_id in event['result']['queue']:
        db_response = db_concerts.get_concert(event['channel_id'], survived_concert_id)
        if db_response is not None:
            concerts_queued.append(db_response)
    random.shuffle(concerts)
    for concert in concerts:
        if len(concerts_queued) < int(os.environ['CONCERT_VOTE_OPTIONS_MAX']):
            print('!!! artist_visited !!!')
            print(artist_visited)
            print('!!! concerts_queued !!!')
            print(concerts_queued)
            artists = concert['artists']
            temp_artist_visited = []
            need_to_be_queued = True
            for artist in artists:
                if artist['name'].lower() not in artist_visited:
                    temp_artist_visited.append(artist['name'].lower())
                else:
                    need_to_be_queued = False
            if need_to_be_queued:
                for temp_artist in temp_artist_visited:
                    artist_visited.append(temp_artist)
                concerts_queued.append(concert)
        else:
            break


    print('!!! NEWLY QUEUED CONCERTS !!!')
    print(concerts_queued)

    if len(concerts_queued) == int(os.environ['CONCERT_VOTE_OPTIONS_MAX']):
        mark_queued_concerts(concerts_queued)
        publish_concert_list(event, concerts_queued)
        time.sleep(2.5)
        publish_voting_ui(event, concerts_queued, artist_visited)
    else:
        out_of_options(event)
        time.sleep(5)
        start_over(event)


def out_of_options(event):
    # print(response.history)
    text = 'Sorry, we couldn\'t find any other concerts matching your music tastes. Let\'s try again.'
    sns_event = {
        'token': event['token'],
        'channel': event['channel_id'],
        'text': text,
    }
    log.info('!!! OUT OF OPTIONS !!!')
    log.info(sns_event)
    sns.publish(
        TopicArn=os.environ['POST_MESSAGE_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def start_over(event):
    event['intents']['genres'] = []
    event['intents']['artists'] = []
    event['intents']['city'] = None
    event['intents']['tastes'] = {}
    db_concerts.remove_unqueued(event['channel_id'])
    """concerts = db_concerts.fetch_concerts(event['sessionAttributes']['channel_id'])
    for concert in concerts:
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
        print(db_response)"""

    sns_event = {
        'team': {
            'team_id': event['team_id'],
            'access_token': event['api_token'],
            'bot': {
                'bot_access_token': event['token']
            }
        },
        'slack': {
            'event': {
                'channel': event['channel_id'],
                'user': event['intents']['host_id'],
                'text': 'THIS ASK TASTE INTENT SHOULD NOT BE INVOKED BY ANY UTTERANCES'
            }
        }
    }

    log.info('!!! START OVER !!!')
    log.info(sns_event)

    sns.publish(
        TopicArn=os.environ['DISPATCH_ACTIONS_SNS_ARN'],
        Message=json.dumps({'default': json.dumps(sns_event)}),
        MessageStructure='json'
    )


def retrieve_intents(event):
    event['intents'] = db_intents.retrieve_intents(
        event['team_id'],
        event['channel_id']
    )


def store_intents(event):
    return db_intents.store_intents(
        keys={
            'team_id': event['team_id'],
            'channel_id': event['channel_id']
        },
        attributes=event['intents']
    )


def handler(event, context):
    log.info(json.dumps(event))
    event = json.loads(event['Records'][0]['Sns']['Message'])
    response = {
        "statusCode": 200
    }
    # try:
    log.info(event)
    count_votes(event)
    retrieve_intents(event)

    # Set the color of the voting button message as grey.
    params = {
        'token': event['api_token'],
        'channel': event['channel_id'],
        'count': 1,
        'inclusive': True,
        'latest': event['intents']['vote_ts'],
        'oldest': event['intents']['vote_ts']
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
            update_message(event)


    event['intents']['vote_ts'] = '0'

    callback_id = event['intents']['callback_id'].split('|')
    event['round'] = callback_id[0]
    if len(callback_id) > 1:
        event['prev_artists'] = callback_id[1]

    print('!!! EVENT RESULT !!!')
    print(callback_id)
    print(event)

    time.sleep(int(os.environ['VOTE_RESULT_WAITING']))
    if event['result']['status'] == STATUS_WINNER:
        show_ticket_link(event)
    elif event['result']['status'] == STATUS_REVOTE:
        execute_second_vote(event)
    elif event['result']['status'] == STATUS_NOPE:
        bring_new_concert_queue(event)
    store_intents(event)


    log.info(response)
    # except Exception as e:
    #     response = {
    #         "statusCode": 400,
    #         "body": json.dumps({"message": str(e)})
    #     }
    #     log.error(response)
    # finally:
    #     return response
