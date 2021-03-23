import json
from requests import post
import sys

print(sys.argv[1])

headers = {'content-type': 'application/json'}

body = json.dumps({'session_id': sys.argv[1], 'setpoint': {'x': 5., 'y': 0., 'z': 0., 'yaw': 0., 'yaw_valid': False}})

res = post('http://localhost:8888/request_access', data=body, headers=headers)

print(res, res.content)
