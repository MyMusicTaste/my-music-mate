# Created by jongwonkim on 07/07/2017.

from .table import DbTable


class DbConcerts(DbTable):
    def __init__(self, name):
        super().__init__(name)

    def add_concert(self, item):
        print('!!! ADD CONCERT DB REQUEST!!!')
        print(item)
        return self.put_item(
            item=item
            # condition_expression='attribute_not_exists(channel_id) OR attribute_not_exists(event_id)'
        )

    def fetch_concerts(self, channel_id):
        response = self.table.query(
            KeyConditionExpression='channel_id = :channel_id AND event_id > :event_id',
            FilterExpression='queued = :queued',
            ExpressionAttributeValues={
                ':channel_id': channel_id,
                ':event_id': '0',
                ':queued': False
            }
        )

        if response['ScannedCount'] == 0:
            return []
        else:
            return response['Items']

    def get_concert(self, channel_id, event_id):
        response = self.table.query(
            KeyConditionExpression='channel_id = :channel_id AND event_id = :event_id',
            ExpressionAttributeValues={
                ':channel_id': channel_id,
                ':event_id': event_id,
            }
        )

        print(response)

        if response['ScannedCount'] == 0:
            return None
        else:
            return response['Items'][0] # We assume there is only one result!

    def remove_unqueued(self, channel_id):
        response = self.table.query(
            KeyConditionExpression='channel_id = :channel_id AND event_id > :event_id',
            FilterExpression='queued = :queued',
            ExpressionAttributeValues={
                ':channel_id': channel_id,
                ':event_id': '0',
                ':queued': False
            }
        )
        for concert in response['Items']:
            self.table.delete_item(
                Key={
                    'channel_id': concert['channel_id'],
                    'event_id': concert['event_id']
                }
            )
        return

    def remove_all(self, channel_id):
        response = self.table.query(
            KeyConditionExpression='channel_id = :channel_id AND event_id > :event_id',
            ExpressionAttributeValues={
                ':channel_id': channel_id,
                ':event_id': '0'
            }
        )
        for concert in response['Items']:
            self.table.delete_item(
                Key={
                    'channel_id': concert['channel_id'],
                    'event_id': concert['event_id']
                }
            )
        return