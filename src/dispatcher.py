# Created by jongwonkim on 11/06/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)


def handler(event, context):
    log.info(json.dumps(event))
    log.info(json.loads(event['Records'][0]['Sns']['Message']))
    response = {
        "statusCode": 200
    }
    return response


