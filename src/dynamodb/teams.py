# Created by jongwonkim on 03/07/2017.

from .table import DbTable


class DbTeams(DbTable):
    def __init__(self, name):
        super().__init__(name)

    def store_team(self, item):
        self.put_item(item=item)

    def retrieve_team(self, team_id):
        response = self.get_item(key={
            'team_id': team_id,
        })

        if 'Item' not in response:
            return {
                'team_id': None,
                'access_token': None,
                'bot': {
                    'bot_access_token': None,
                    'bot_user_id': None
                },
                'ok': False,
                'scope': None,
                'team_name': None,
                'user_id': None
            }
        item = response['Item']
        return item

