# Created by jongwonkim on 04/07/2017.

import logging
import boto3
import re

log = logging.getLogger()
log.setLevel(logging.DEBUG)


class LexRunTime(object):
    def __init__(self, name, alias):
        self.name = name
        self.alias = alias
        self.lex = boto3.client('lex-runtime')

    @staticmethod
    def filter_message(self, message):
        message = re.sub('<@', '@', message)
        message = re.sub('>', '', message)
        return message

    def post_message(self, team_id, channel_id, api_token, bot_token, caller_id, message):
        message = self.filter_message(channel_id, message)

        return self.lex.post_text(
            botName=self.name,
            botAlias=self.alias,
            userId=api_token,
            sessionAttributes={
                'team_id': team_id,
                'channel_id': channel_id,
                'api_token': api_token,
                'bot_token': bot_token,
                'caller_id': caller_id
            },
            inputText=message
        )
