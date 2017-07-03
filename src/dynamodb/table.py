# Created by jongwonkim on 03/07/2017.

import logging
import boto3

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')


class DbTable(object):
    def __init__(self, name):
        self.name = name
        self.table = dynamodb.Table(name)

    def put_item(self, item):
        return self.table.put_item(Item=item)

    def get_item(self, key):
        return self.table.get_item(Key=key)
