# Created by jongwonkim on 07/07/2017.

from .table import DbTable


class DbConcerts(DbTable):
    def __init__(self, name):
        super().__init__(name)

    def add_concert(self, item):
        return self.put_item(
            item=item,
            condition_expression='attribute_not_exists(channel_id) AND attribute_not_exists(event_id)'
        )

    def fetch_concerts(self, channel_id):
        response = self.table.query(
            KeyConditionExpression='channel_id = :channel_id AND event_id > :event_id',
            ExpressionAttributeValues={
                ':channel_id': channel_id,
                ':event_id': '0'
            }
        )

        print(response)

        if response['ScannedCount'] == 0:
            return []
        else:
            return response['Items']
