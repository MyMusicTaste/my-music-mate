# Created by jongwonkim on 03/07/2017.

from .table import DbTable


class DbTeams(DbTable):
    def __init__(self, name):
        super().__init__(name)

    def store_team(self, item):
        self.put_item(item=item)

    def retrieve_team(self, team_id):
        return self.get_item(key={
            'team_id': team_id,
        })

