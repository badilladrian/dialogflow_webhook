import json
from requests import get, post

body = json.dumps({'event_type': 'find',
                   'event_id': 'B97B2A2A-5578-4138-AAF6-E732EB7E2EE0',
                   'token': '0x68aad0248835378caa1e5b2051be35a5ff1ded828786cfc',
                   'token_check_url': 'https://mytoken.com/check',
                   'poi': {
                       'lat': 37.42946136677789,
                       'long': -122.0829051733017,
                       'alt': 5.,
                       'wait_time': 10.,
                       'clearance': 10.0,
                   },
                   'stream_url': '"rtmp://90.1.34.1:8711/live'})
#
# body = json.dumps({'event_type':'find',
#                    'event_id':'B97B2A2A-5578-4138-AAF6-E732EB7E2EE0',
#                    'token':'0x68aad0248835378caa1e5b2051be35a5ff1ded828786cfc',
#                    'token_check_url':'https://mytoken.com/check',
#                    'poi':{
#                        'lat':37.42941249785454,
#                        'long':-122.08391100168228,
#                        'alt':10.,
#                        'wait_time': 20.,
#                        'clearance': 5.0,
#                    },
#                    'stream_url':'"rtmp://90.1.34.1:8711/live'})

headers = {'content-type': 'application/json'}
print(post('http://localhost:8888/start_new_session', data=body, headers=headers).content)

# body1 = json.dumps({'session_id': 'S0015166258190634'})
# print post('http://localhost:8888/access_session', data = body1, headers=headers).content
