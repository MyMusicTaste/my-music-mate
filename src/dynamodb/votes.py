# Created by jongwonkim on 09/07/2017.

from .table import DbTable


class DbVotes(DbTable):
    def __init__(self, name):
        super().__init__(name)

    def store_vote(self, item):
        self.put_item(item=item)

    def fetch_votes(self, channel_id):
        response = self.table.query(
            KeyConditionExpression='channel_id = :channel_id AND begins_with(user_id, :user_id)',
            ExpressionAttributeValues={
                ':channel_id': channel_id,
                ':user_id': '_'
            }
        )

        if response['ScannedCount'] == 0:
            return []
        else:
            return response['Items']

    def remove_previous(self, channel_id, user_id):
        response = self.table.delete_item(
            Key={
                'channel_id': channel_id,
                'user_id': user_id
            }
        )
        return response

    def reset_votes(self, channel_id):
        response = self.table.query(
            KeyConditionExpression='channel_id = :channel_id AND begins_with(user_id, :user_id)',
            ExpressionAttributeValues={
                ':channel_id': channel_id,
                ':user_id': '_'
            }
        )
        for vote in response['Items']:
            self.table.delete_item(
                Key={
                    'channel_id': vote['channel_id'],
                    'user_id': vote['user_id']
                }
            )
        return
