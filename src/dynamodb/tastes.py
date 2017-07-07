# Created by jongwonkim on 07/07/2017.

from .table import DbTable


class DbTastes(DbTable):
    def __init__(self, name):
        super().__init__(name)

    def add_taste(self, taste_name, taste_type, interest):
        self.put_item(item={
                'taste_name': taste_name.lower(),
                'display_name': taste_name,
                'taste_type': taste_type,
                'interest': interest.lower()
            },
            # ConditionExpression='attribute_not_exists(taste_name) AND attribute_not_exists(taste_type)'
            ConditionExpression=''
        )
