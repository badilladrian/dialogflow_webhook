import tornado.ioloop
import tornado.web
import json
import urllib
import time
from tornado import httpclient
from tornado.httpclient import AsyncHTTPClient
from tornado import gen
from math import radians, cos, sin, asin, sqrt
import hashlib
import time


# mission sample code
# url : localhost:8899/drone/
# {
# 	"lat":37.42946671749694,
# 	"lng":-122.08247733765029,
# 	"alt":5,
# 	"wait_time":10
# }
#
# drone control sample code
# url : localhost:8899/interrupt/1
#
# {
# 	"mission_token":123, //token id form mission
#   "move":"up", //none, up, down, left, right, forward, backward
#   "yaw":"none", //none, clockwise, anticlockwise
#   "wait":10 // seconds
# }
#
#  drone get status sample code
# url : localhost:8899/get/1
#
# {
# 	"mission_token":123, //token id form mission
# }
#


count = 0


drone = {
    1: {'header': {
        'Authorization': 'Token 20fe4f04fe765cf265b81dbccd54a74303deba39',
        'VehicleID': '1atcQaG8'},
        'busy': 0,
        'going_to': '',
        'mission_wait': 0,
        'battery': 0,
        'location': {
            'lat': 0,
            'lng': 0,
            'alt': 0
        },
        'home_location': {
            'lat': 0,
            'lng': 0,
            'alt': 0
        },
        'mission_location': {
            'lat': 0,
            'lng': 0,
            'alt': 0
        },
        'hold_mission': {
            'last_going_to':'',
            'return_location':{
                'lat': 0,
                'lng': 0,
                'alt': 0
            },
        }
    },
    2: {'header': {
        'Authorization': 'Token 84d440b0ba95c19ccd8e56a2cf0e540694798850',
        'VehicleID': 'r6nRDos0'},
        'busy': 0,
        'going_to': '',
        'mission_wait': 0,
        'battery': 0,
        'location': {
            'lat': 0,
            'lng': 0,
            'alt': 0
        },
        'home_location': {
            'lat': 0,
            'lng': 0,
            'alt': 0
        },
        'mission_location': {
            'lat': 0,
            'lng': 0,
            'alt': 0
        },
        'hold_mission': {
            'last_going_to':'',
            'return_location':{
                'lat': 0,
                'lng': 0,
                'alt': 0
            },
        }
    }

}

# main process
def update_status():
    global count
    global drone
    count += 1
    header1 = drone[1]['header']
    header2 = drone[2]['header']
    print(count)
    def update_dron1(response):
        if response.error:
            print("Drone 1 Error is : %s" % response.error)
            return
        else:
            try:
                resjson = json.loads(response.body)
                if type(resjson['latitude']) == float:
                    drone[1]['location']['lat'] = resjson['latitude']
                    drone[1]['location']['lng'] = resjson['longitude']
                    print("Drone 1: ", drone[1]['location']['lat'], drone[1]['location']['lng'])
            except:
                return
    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/mavros/global_position/global", update_dron1, headers=header1, request_timeout=30. )

    def update_dron2(response):
        if response.error:
            print("Drone 2 Error is : %s" % response.error)
            return
        else:
            try:
                resjson = json.loads(response.body)
                if type(resjson['latitude']) == float:
                    drone[2]['location']['lat'] = resjson['latitude']
                    drone[2]['location']['lng'] = resjson['longitude']
                    print("Drone 2: ", drone[2]['location']['lat'], drone[2]['location']['lng'])
            except:
                return
    http_client = AsyncHTTPClient()
    # http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/mavros/global_position/global", update_dron2, headers=header2, request_timeout=30.)


def start_stream(drone_id):
    global drone
    header = drone[drone_id]['header']
    url = 'https://dev.flytbase.com/rest/ros/flytsim/video_streaming/start_raspicam_stream',
    body=json.dumps({"image_width": 0,
                     "image_height": 0,
                     "framerate": 0,
                     "brightness": 0,
                     "saturation": 0,
                     "flip": True,
                    "remote_url": "rtmp://40.69.56.29:1935/livedrone/myStream",
                     "remote_target": True})
    def stream_start_response(response):
        print (response.body)
        if response.error:
            print("Stream start Error: %s" % response.error)
        else:
            print('Streaming started...')
    http_client = AsyncHTTPClient()
    http_client.fetch(url, stream_start_response, method='POST', headers=header, body=body, request_timeout=180.0)

def stop_stream(drone_id):
    global drone
    header = drone[drone_id]['header']
    url = 'https://dev.flytbase.com/rest/ros/flytsim/video_streaming/stop_raspicam_stream'
    def stream_stop_response(response):
        print (response.body)
        if response.error:
            print("Stream stop Error: %s" % response.error)
        else:
            print('Streaming Stoped...')
    http_client = AsyncHTTPClient()
    http_client.fetch(url, stream_stop_response, method='GET', headers=header, request_timeout=180.0)


def takeoff(drone_id, alt):
    global drone
    header = drone[drone_id]['header']
    # print (header)
    drone[drone_id]['busy'] = 1
    body = json.dumps({"takeoff_alt": alt})
    print (body)
    def takeoff_response(response):
        print (response.body)
        if response.error:
            print("takeoff Error: %s" % response.error)
        else:
            print(response.body)
            print('Going to mission')
            drone[drone_id]['going_to'] = 'Mission'
            go(drone_id)
    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/take_off", takeoff_response, method='POST', headers=header, body=body, request_timeout=180.0)


def go(drone_id):
    global drone
    header=drone[drone_id]['header']
    body = json.dumps({
                   "lat_x" : drone[drone_id]["mission_location"]['lat'],
                   "long_y" : drone[drone_id]["mission_location"]['lng'],
                   "rel_alt_z": drone[drone_id]["mission_location"]['alt'],
                   "yaw": 0.0,
                   "tolerance": 2.0,
                   "async": False,
                   "yaw_valid": True
                   })

    @gen.engine
    def go_handle_response(response):
        if response.error:
            print("Error: %s" % response.error, "GO")
            go(drone_id)
        else:
            print(response.body, "GO RESP")
            resp = json.loads(response.body)
            if resp['success'] == False:
                if drone[drone_id]['going_to'] == 'Mission':
                    print ('time out but continue to mission')
                    go(drone_id)
                else:
                    print('going to ', drone[drone_id]['going_to'])
            elif resp['success'] == True:
                print('Reached to Mission Point')
                wait_time = int(drone[drone_id]['mission_wait'])
                print('Wait for sec : ', wait_time)
                # yield gen.sleep(wait_time)
                drone[drone_id]['going_to'] = 'Home'
                print("Mission Complete Returning to home")
                go_home(drone_id)

                # def hand_resp(response):
                #     drone[drone_id]['busy'] = 0
                #     print "Mission Complete Returning to home"
                # http_client = AsyncHTTPClient()
                # http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/rtl", hand_resp, method='GET', headers=header)

    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/position_set_global", go_handle_response,
                      method='POST', headers=header, body=body, request_timeout=240.)


def go_home(drone_id):
    global drone
    header=drone[drone_id]['header']
    body = json.dumps({
                   "lat_x" : drone[drone_id]["home_location"]['lat'],
                   "long_y" : drone[drone_id]["home_location"]['lng'],
                   "rel_alt_z": 5.00,
                   "yaw": 0.0,
                   "tolerance": 2.0,
                   "async": False,
                   "yaw_valid": True
                   })
    print(body)
    def go_home_handle_response(response):
        if response.error:
            print("Error: %s" % response.error, "GO HOME")
            go_home(drone_id)
        else:
            print(response.body, "GO HOME RESP")
            resp = json.loads(response.body)
            if resp['success'] == False:
                if drone[drone_id]['going_to'] == 'Home':
                    print ('time out but continue to Home')
                    go_home(drone_id)
                else:
                    print('going to ', drone[drone_id]['going_to'])
            if resp['success'] == True:
                print('Reached at home, Landing...')
                land(drone_id)

    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/position_set_global", go_home_handle_response, method='POST', headers=header, body=body, request_timeout=240.)


def land(drone_id):
    global drone
    header = drone[drone_id]['header']
    body = json.dumps({"async": False})
    def land_resp(response):
        print(response.body)
        print('Mission Completed')
        # stop_stream(drone_id)
        drone[drone_id]['mission_token'] = ''
        drone[drone_id]['going_to'] = ''
        drone[drone_id]['busy'] = 0
    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/land", land_resp, method='POST', headers=header, body=body)


def calc_dist(lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        # Radius of earth in kilometers is 6371
        mtr = 6371000 * c
        return mtr
# end main process

# intrept process

def hold(drone_id,wait_time):
    global drone
    header = drone[drone_id]['header']
    @gen.engine
    def hold_resp(response):
        print("Drone Paused")
        update_status()
        drone[drone_id]['hold_mission']['last_going_to'] = drone[drone_id]['going_to']
        drone[drone_id]['going_to'] = 'Hold'
        drone[drone_id]['hold_mission']['return_location']['lat'] = drone[drone_id]['location']['lat']
        drone[drone_id]['hold_mission']['return_location']['lng'] = drone[drone_id]['location']['lng']
        drone[drone_id]['hold_mission']['return_location']['alt'] = drone[drone_id]['location']['alt']
        # pause for time
        # wait_time = 60
        # yield gen.sleep(wait_time)
        resume(drone_id)

    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/position_hold", hold_resp, method='GET', headers=header)

def resume(drone_id):
    global drone
    header = drone[drone_id]['header']
    body = json.dumps({
        "lat_x": drone[drone_id]['hold_mission']['return_location']['lat'],
        "long_y": drone[drone_id]['hold_mission']['return_location']['lng'],
        "rel_alt_z": drone[drone_id]['hold_mission']['return_location']['alt'],
        "yaw": 0.0,
        "tolerance": 2.0,
        "async": False,
        "yaw_valid": True
    })

    def resume_handle_response(response):
        if response.error:
            print("Error: %s" % response.error, "GO")
            go(drone_id)
        else:
            print(response.body, "GO RESP")
            resp = json.loads(response.body)
            if resp['success'] == False:
                if drone[drone_id]['going_to'] == 'Hold':
                    print ('time out but continue to mission')
                    resume(drone_id)
                else:
                    print('going to ', drone[drone_id]['going_to'])
            elif resp['success'] == True:
                drone[drone_id]['going_to'] = drone[drone_id]['hold_mission']['last_going_to']
                if drone[drone_id]['hold_mission']['last_going_to'] == 'Mission':
                    print ('Waiting over continue to mission')
                    go(drone_id)
                elif drone[drone_id]['hold_mission']['last_going_to'] == 'Home':
                    print ('Waiting over continue to home')
                    go_home(drone_id)

    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/position_set_global", resume_handle_response,
                      method='POST', headers=header, body=body, request_timeout=240.)


def doit(drone_id,drone_json,wait_time):
    global drone
    header = drone[drone_id]['header']
    # print (header)
    body = json.dumps(drone_json)
    print (body)
    def todo_handle(response):
        print (response.body)
        print(drone[drone_id], "respond received : ")
        if response.error:
            print("Error: %s" % response.error)
        else:
            # wait for wait_time
            print(response.body)
            print('Done')
    http_client = AsyncHTTPClient()
    http_client.fetch("http://dev.flytbase.com/rest/ros/flytsim/navigation/position_set", todo_handle, method='POST', headers=header, body=body)

# end intrept process

class DroneHandler(tornado.web.RequestHandler):
    @gen.engine
    def post(self):
        if self.request.headers["Content-Type"].startswith("application/json"):
            global drone
            # print (id)
            self.json_args = json.loads(self.request.body)
            drone_dist = {}

            #currently considering only 2 drones
            drone_dist[1] = calc_dist(drone[1]['location']['lng'], drone[1]['location']['lat'], self.json_args["lng"], self.json_args["lat"])
            drone_dist[2] = calc_dist(drone[2]['location']['lng'], drone[2]['location']['lat'], self.json_args["lng"], self.json_args["lat"])
            if drone_dist[1] < drone_dist[2] and drone[1]['busy'] == 0:
                available_drone = 1
                success = True
            elif drone[2]['busy'] == 0:
                available_drone = 2
                success = True
            else:
                available_drone = 0
                success = False
                return
            mission_token = hashlib.md5(str(time.time()).encode("utf")).hexdigest()

            # temp drone 1 select code
            if drone[1]['busy'] == 0:
                available_drone = 1
            else:
                responce = {'success': False, 'drone_id': available_drone, 'message': "No Drone is available"}
                self.write(responce)
                self.finish()
                return
            #temp code is over

            print("Available nearest drone ID is : ", available_drone)
            drone[available_drone]['mission_location']['lat'] = self.json_args["lat"]
            drone[available_drone]['mission_location']['lng'] = self.json_args["lng"]
            drone[available_drone]['mission_location']['alt'] = self.json_args["alt"]
            drone[available_drone]['mission_wait'] = self.json_args["wait_time"]
            drone[available_drone]['mission_token'] = mission_token

            print("Current Location at takeoff point is set as home location")
            drone[available_drone]['home_location']['lat'] = drone[available_drone]['location']['lat']
            drone[available_drone]['home_location']['lng'] = drone[available_drone]['location']['lng']
            # start_stream(available_drone)
            takeoff(available_drone, self.json_args['alt'])
            # land(available_drone)
            responce = {'success': success, 'drone_id': available_drone, 'mission_token': mission_token}
            self.write(responce)
            self.finish()


class Dronedo(tornado.web.RequestHandler):
    @gen.engine
    def post(self,id):
        if self.request.headers["Content-Type"].startswith("application/json"):
            global drone
            print (id)
            # yield gen.sleep(10)
            self.json_args = json.loads(self.request.body)
            drone_id = int(id)
            token = str(self.json_args["mission_token"])
            move = str(self.json_args["move"])
            yaw = str(self.json_args["yaw"])
            wait = int(self.json_args["wait"])
            # if drone[drone_id]['mission_token'] == token:
            #     success = True
            # else:
            #     success = False
            drone_json = {
                "x": 0,
                "y": 0,
                "z": 0,
                "yaw": 0,
                "tolerance": 1.0,
                "async": True,
                "relative": True,
                "yaw_valid": False,
                "body_frame": True
            }

            if move == "left":
                drone_json['y'] = -1.0
            elif move == "right":
                drone_json['y'] = 1.0
            else:
                drone_json['y'] = 0.0

            if move == "forward":
                drone_json['x'] = 1.0
            elif move == "backward":
                drone_json['x'] = -1.0
            else:
                drone_json['x'] = 0.0

            if move == "up":
                drone_json['z'] = -1.0
            elif move == "down":
                drone_json['z'] = 1.0
            else:
                drone_json['z'] = 0.0

            if yaw == "clockwise":
                drone_json['yaw'] = 0.523598776
                drone_json['yaw_valid'] = True
            elif yaw == "anticlockwise":
                drone_json['yaw'] = -0.523598776
                drone_json['yaw_valid'] = True
            else:
                drone_json['yaw'] = 0.0
                drone_json['yaw_valid'] = False
            # hold(drone_id,wait)
            doit(drone_id,drone_json,wait)
            responce = {'success': 1}
            self.write(responce)
            self.finish()


class Droneget(tornado.web.RequestHandler):
    @gen.engine
    def post(self,id):
        if self.request.headers["Content-Type"].startswith("application/json"):
            global drone
            # print (id)
            drone_id = int(id)
            responce = {'drone': drone[drone_id]}
            self.write(responce)
            self.finish()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        print('Welcome to Flytbase')


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/drone/", DroneHandler),
        (r"/get/(.*)", Droneget),
        (r"/interrupt/(.*)", Dronedo),
    ])


if __name__ == "__main__":
    update_status()
    app = make_app()
    app.listen(8899)
    tornado.ioloop.PeriodicCallback(update_status, 30000).start()
    tornado.ioloop.IOLoop.current().start()
