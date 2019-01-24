import os
import json

if 'LAMBDA_TASK_ROOT' in os.environ:
    dir = os.environ['LAMBDA_TASK_ROOT']
else:
    dir = "."

with open(dir + '/config.json', 'r') as cf:
    config = json.load(cf)
