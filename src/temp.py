# Created by jongwonkim on 24/06/2017.

import os
import logging
import boto3
import json
from urllib.parse import urlencode
import requests

log = logging.getLogger()
log.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    log.info(json.dumps(event))
    try:

        response = {
            "statusCode": 200,
            "body": "A test purpose lambda function."
        }
        log.info(response)
        return response
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }
        log.error(response)
        return response
