import asyncio
import tornado.ioloop
import tornado.web
import json
import urllib
import time
from tornado import httpclient
from tornado import httputil
from tornado.web import RequestHandler, asynchronous
#GFM from tornado import gen


count = 1


def counter():
    global count
    count = count + 1
    print(count)


class DroneHandler(tornado.web.RequestHandler):
    #@asynchronous
    #@gen.engine
    async def get(self, drone_id):
        global count
        # try:
        #     drone_id = int(drone_id)
        #     print('Drone_id: {} is integer'.format(drone_id))
        #     count = drone_id
        #     print('count changed to drone_id:{}'.format(count))
        # except Exception as e:
        #     print('could not convert drone_id: {} to integer'.format(drone_id))
        #     print('count not changed:{}'.format(count))
        print (count)

        #GFM yield gen.sleep(5)
        await asyncio.sleep(5)
        responce= {"count" :count }
        self.write(responce)
        self.finish()


    def post(self,id):
        global count

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        print('Hello')

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/drone/(.*)", DroneHandler),
    ])


if __name__ == "__main__":
    counter()
    app = make_app()
    app.listen(8899)
    tornado.ioloop.PeriodicCallback(counter, 1000).start()
    tornado.ioloop.IOLoop.current().start()