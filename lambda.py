from config import config
import generator

import os
import json

def response(code, msg):
    return {
        "isBase64Encoded": False,
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(msg)
    }

def success(msg):
    return response(200, msg)

def error(msg):
    return response(500, msg)

def denied(msg):
    return response(403, msg)

def handler(event, context):
    if event['body'] != json.dumps(config['password']):
        return denied("Bad authentication string")
    try:
        if "git" in config:
            generator.checkout()
        os.chdir(config['data_dir'])
        generator.main()
        return success('OK')
    except Exception as e:
        return error(getattr(e, 'message', repr(e)))
