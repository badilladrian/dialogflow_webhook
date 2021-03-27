import tornado.ioloop
import tornado.web
import json
import urllib
import time
from tornado import httpclient
from tornado.httpclient import AsyncHTTPClient

from tornado.web import RequestHandler, asynchronous
#GFM from tornado import gen

dron = {
    1: {'header': {
            'Authorization': 'Token 20fe4f04fe765cf265b81dbccd54a74303deba39',
            'VehicleID': 'cAHoOyIi'},
            'busy': 0,
            'location': {
                'lat': 40.748817,
		        'lng': -73.985428,
                'alt': 5},
            'battery' : 0
        }
    }


def takeoff(header,alt):
    body = json.dumps({"takeoff_alt": alt})
    def handle_response(response):
        if response.error:
            print("Error: %s" % response.error)
        else:
            print(response.body)

    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/take_off", handle_response, method='POST', headers=header, body=body)


count = 1

def update_status():
    global count
    count = count + 1
    print(count)

class DroneHandler(tornado.web.RequestHandler):
    #GFM @asynchronous
    async def post(self, id):
        alt = int(id)
        global dron
        header = dron[1]['header']
        takeoff(header,alt)
        self.write('done')
        self.finish()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        print('Hello')


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/drone/(.*)", DroneHandler),
    ])


if __name__ == "__main__":
    update_status()
    app = make_app()
    app.listen(8899)
    tornado.ioloop.PeriodicCallback(update_status, 5000).start()
    tornado.ioloop.IOLoop.current().start()
