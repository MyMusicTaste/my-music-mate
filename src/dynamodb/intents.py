# Created by jongwonkim on 05/07/2017.

from .table import DbTable


class DbIntents(DbTable):
    def __init__(self, name):
        super().__init__(name)

    def store_intents(self, keys, attributes):
        item = {}
        for k in keys:
            item[k] = keys[k]
        for a in attributes:
            item[a] = attributes[a]
        self.put_item(item=item)

    def retrieve_intents(self, team_id, channel_id):
        response = self.get_item(
            key={
                'team_id': team_id,
                'channel_id': channel_id
            },
            attributes_to_get=[
                'host_id',
                'current_intent',
                'mates',
                'lounge',
                'genres',
                'artists',
                'city',
                'tastes'
            ]
        )

        if 'Item' not in response:
            return {
                'host_id': None,
                'current_intent': None,
                'mates': [],
                'lounge': {
                    'id': None,
                    'name': None
                },
                'genres': [],
                'artists': [],
                'city': None,
                'tastes': {},
                'round': 0,
                'timeout': 0,
            }
        item = response['Item']
        if 'host_id' not in item:
            item['host_id'] = None
        if 'current_intent' not in item:
            item['current_intent'] = None
        if 'mates' not in item:
            item['mates'] = []
        if 'lounge' not in item:
            item['lounge'] = {
                'id': None,
                'name': None
            }
        if 'genres' not in item:
            item['genres'] = []
        if 'artists' not in item:
            item['artists'] = []
        if 'city' not in item:
            item['city'] = None
        if 'tastes' not in item:
            item['tastes'] = {}
        if 'round' not in item:
            item['round'] = 0
        if 'timeout' not in item:
            item['timeout'] = 0
        return item

    def switch_channel(self, channel_id, keys, attributes):
        self.delete_item(keys)
        keys['channel_id'] = channel_id
        return self.store_intents(keys=keys, attributes=attributes)
