# Created by jongwonkim on 03/07/2017.

import logging
import boto3

log = logging.getLogger()
log.setLevel(logging.DEBUG)


class DbTable(object):
    def __init__(self, name):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(name)

    def put_item(self, item, condition_expression=None):
        if condition_expression is None:
            return self.table.put_item(Item=item)
        else:
            return self.table.put_item(Item=item, ConditionExpression=condition_expression)

    def get_item(self, key, attributes_to_get=None):
        if attributes_to_get is None:
            return self.table.get_item(Key=key)
        else:
            return self.table.get_item(Key=key, AttributesToGet=attributes_to_get)

    def delete_item(self, key):
        return self.table.delete_item(Key=key)

