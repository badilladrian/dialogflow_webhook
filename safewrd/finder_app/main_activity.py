"""
FLYTBASE INC grants Customer a perpetual, non-exclusive, royalty-free license to use this software.
 All copyrights, patent rights, and other intellectual property rights for this software are retained by FLYTBASE INC.
"""
"""
    Update library Tornado 6.1
    Author: Giovanni Fonseca
    Date due: 25-03-2021
"""

import operator

import asyncio
from tornado.concurrent import Future 
from redis import Redis, StrictRedis, ConnectionPool
from tornado.web import Application, RequestHandler
import sys
from tornado import ioloop
import json
import time
import requests

from helper import WebSocketClient, dist_bet_coordinates, DroneRemoteAccess
# from session import SessionHandler
from redis_session.tornado_session import SessionHandler

# Initialize redis client
redis_main = Redis(host='localhost')

# set parameters
drone_status_update_rate = 4000  # data will be updated every T mili seconds.
sub_topics = ["gpos", "lpos", 'imu', "battery"]  # topics to be subscribed


def init_redis_structures(drone_list):
    """ update initial structures on redis server
    """
    counter = 0
    drone_dict = {}
    for drone in drone_list:
        counter += 1
        name = "SFRD00" + str(counter)

        # initialize per drone structure
        redis_main.set(drone['vehicle_id'] + "_status", 0)
        redis_main.set(drone['vehicle_id'] + "_ns", drone['namespace'])
        redis_main.set(drone['vehicle_id'] + "_name", name)
        redis_main.set(drone['vehicle_id'] + "_api_key", drone['api_key'])
        redis_main.set(drone['vehicle_id'] + "_gpos", json.dumps({"lat": 0., "long": 0., "alt": 0.}))
        redis_main.set(drone['vehicle_id'] + "_lpos", json.dumps({"x": 0., "y": 0., "z": 0., "yaw": 0.}))
        redis_main.set(drone['vehicle_id'] + "_batt", json.dumps({"percent": 0.}))
        redis_main.set(drone['vehicle_id'] + "_imu", json.dumps({"yaw": 0.}))

        drone_dict[drone['vehicle_id']] = {"name": name}

    # initialize vehicles structure.
    redis_main.set("vehicles", json.dumps(drone_dict))

    # initialize sessions list
    sessions_list = json.dumps({"F000": {"session_key": "asaasdfk532gf"}})
    redis_main.set("sessions", sessions_list)


def confirm_drones(drone_list):
    """confirm each drone is valid and live by querying namespace
    """
    liveDrones = []
    for drone in drone_list:
        headers = {'Authorization': 'Token ' + drone['api_key'], 'VehicleID': drone['vehicle_id']}
        try:
            resp = requests.get('https://dev.flytbase.com/rest/ros/get_global_namespace', headers=headers)
            if resp.status_code == 200:
                try:
                    resp = resp.json()
                    if resp['success']:
                        ns = resp['param_info']['param_value']
                        drone_temp = drone.copy()
                        drone_temp['namespace'] = ns
                        liveDrones.append(drone_temp)
                except ValueError:
                    print("wrong result")
            elif resp.status_code == 404:
                print(drone["vehicle_id"], "Drone not reachable, discarding!")
            else:
                print(resp.status_code, " Error, discarding drone")
        except (requests.ConnectionError, requests.Timeout):
            print("No internet connection")
    return liveDrones


# @gen.engine
# def get_drone_status(list_of_drones):
#     """
#     Use list of vehicles and per drone keys to fetch current drone status.
#     On it's first successful execution (for first drone) set the app ready flag.
#     :return:
#     """
#     drone_list = list_of_drones
#     for drone in drone_list:
#         # fetch recent updates.
#         gpos = yield gen.Task(redis_main.get, drone + '_gpos')
#         lpos = yield gen.Task(redis_main.get, drone + '_lpos')
#         batt = yield gen.Task(redis_main.get, drone + '_batt')
#         # update each drones info topic.
#         try:
#             gpos = json.loads(gpos)
#             lpos = json.loads(lpos)
#             batt = json.loads(batt)
#             veh_details = drone_list[drone]
#             updated_state = json.dumps(
#                 {"state": {"lat": gpos['lat'], "long": gpos['long'], "alt": lpos['z'],
#                            "yaw": lpos['yaw'], "bat": batt['percent']},
#                  "status": veh_details['status'], "ns": veh_details['ns'], "name": veh_details['name']})
#             yield gen.Task(redis_main.set, drone + '_info', updated_state)
#
#             # update app status
#             app_status = yield gen.Task(redis_main.get, "app_info")
#             try:
#                 app_status = json.loads(app_status)
#                 app_stat = app_status["status"]
#                 if app_stat == 1:
#                     yield gen.Task(redis_main.set, "app_info", json.dumps({"status": 0}))
#                     # todo remove this testing line
#                     # test_session()
#             except ValueError:
#                 print("app status json decode failed"
#                 # setting up app not running flag.
#                 yield gen.Task(redis_main.set, "app_info", json.dumps({"status": 2}))
#         except ValueError:
#             print("drone json array decode failed"

async def find_available_drone(lat, long):    
    """
    Query all current vehicle topics and query their status.
    Find list of all available drones.
    Find the closest one out of them.
    Test if the drone is available, if not mark it as 'not available'.
    Go for second closest.
    :return:
    """
    list_drones = await asyncio.Task(redis_main.get, "vehicles")
    
    try:
        list_drones = json.loads(list_drones)
        dronelist = list_drones.keys()
        # print(dronelist, "master list"
        available_drones = []
        for drone in dronelist:
            # if drone is available use it otherwise discard.
            status = await asyncio.Task(redis_main.get, drone + '_status')
            if status == '0':
                available_drones.append(drone)
        # print(available_drones, "available"
        if len(available_drones) > 0:
            a_drones = {}
            for drone in available_drones:
                # for each available drone find it's location.
                locationJ = await asyncio.Task(redis_main.get, drone + '_gpos')
                location = json.loads(locationJ)
                dist = dist_bet_coordinates(long, lat, location['long'], location['lat'])
                a_drones[drone] = dist
            # print(a_drones, "closest dict"
            closest_drone = None
            try:
                closest_drone = min(a_drones.iteritems(), key=operator.itemgetter(1))[0]
            except ValueError:
                print("DroneFinder: black hole situation")
            # todo validate again if closest drone is available
            raise await asyncio(closest_drone)
        else:
            print("DroneFinder: No available drones")
            raise await asyncio.Return(False)
        
    except (ValueError, KeyError, IndexError) as error:
        print(error, error.args, "DroneFinder: decode failed")
        raise await asyncio.Return(False)


async def test_session():
    newSession = SessionHandler('S001', 'abcd123', '6gi14TJq', '84d440b0ba95c19ccd8e56a2cf0e540694798850', 'flytsim',
                                'SFRD001', {'lat': 37.430289043924745, 'long': -122.08234190940857, 'alt': 10.},
                                10., 20., "rtmp://40.69.56.29:1935/livedrone/myStream")
    # newSession = SessionHandler('S001', 'abcd123', 'r6nRDos0', '84d440b0ba95c19ccd8e56a2cf0e540694798850','flytsim',
    #                             'SFRD001', {'lat':37.42963991886908,'long':-122.08431735634804, 'alt':10.},
    #                             10.,10.,"rtmp://40.69.56.29:1935/livedrone/myStream")
    
    await newSession.run_mission()


class MainHandler(RequestHandler):
    async def get(self):
        self.write("Welcome to Drone Manager")
        self.finish()


class DroneSessionHandler(RequestHandler):
    async def post(self):
        if self.request.headers["Content-Type"].startswith("application/json"):
            dataJ = self.request.body.decode("UTF-8")
            try:
                data = json.loads(dataJ)
                self.event_type = data["event_type"]
                self.event_id = data["event_id"]
                self.safe_token = data["token"]
                self.token_url = data["token_check_url"]
                self.poi_lat = data['poi']['lat']
                self.poi_long = data['poi']['long']
                self.poi_alt = data['poi']['alt']
                self.poi_wait_time = data['poi']['wait_time']
                self.poi_clearance = data['poi']['clearance']
                self.stream_url = data['stream_url']

                # valid request. Verify if app is ready, if not ask user to try again.
                # if app ready, check if a drone is available, if not ask user to try again.
                # if drone available, create new session, return session ID to user.
                
                available_drone = await find_available_drone(self.poi_lat, self.poi_long)                
                if available_drone:
                    # start the session, first part.
                    self.session_name = 'S00' + str(int(time.time() * 10000))
                    self.droneID = available_drone
                    # mark the drone as busy even before creating new session.
                    await asyncio.Task(redis_main.set, self.droneID + '_status', 1)

                    # Miguel: Comenté esto porque estaba dando error después del yield
                    # Giovanni: Actualice los metodos del Tornado y corrigio el problema que comento Miguel
                    print("Creating new Session: ", self.session_name, " Drone: ", self.droneID)
                    self.api_key = await asyncio.Task(redis_main.get, self.droneID + '_api_key')
                    self.ns = await asyncio.Task(redis_main.get, self.droneID + '_ns')
                    self.drone_name = await asyncio.Task(redis_main.get, self.droneID + '_name')
                    newSession = SessionHandler(self.session_name, self.droneID, self.api_key, self.ns, self.drone_name,
                                                {'lat': self.poi_lat, 'long': self.poi_long, 'alt': self.poi_alt},
                                                self.poi_alt, self.poi_clearance, self.poi_wait_time, self.stream_url)
                    newSession.run_mission()
                    print("SessionManager: Will complete mission in background")
                    #
                    self.write(self.session_name)
                    self.finish()
                else:
                    self.write("All drones busy, try again later")
                    self.finish()
            except (ValueError, KeyError) as error:
                print("session request decode failed ", error)
                self.set_status(400, "unsupported input, JSON required")
                self.finish()
        else:
            self.set_status(400, "JSON input required")
            self.finish()


class SessionAccessHandler(RequestHandler):
    async def post(self):
        if self.request.headers["Content-Type"].startswith("application/json"):
            dataJ = self.request.body.decode("UTF-8")
            try:
                data = json.loads(dataJ)
                self.session_id= data['session_id']
                self.sp_x = data['setpoint']['x']
                self.sp_y = data['setpoint']['y']
                self.sp_z = data['setpoint']['z']
                self.sp_yaw = data['setpoint']['yaw']
                self.sp_yaw_valid = data['setpoint']['yaw_valid']
                session_status = await asyncio.Task(redis_main.get, self.session_id+'_status')
                
                # print(session_status
                if session_status:
                    if session_status == '4':
                        print("RemoteAccess: session ready, trying to acquire drone access lock")

                        # gather session and drone information
                        await asyncio.Task(redis_main.set, self.session_id + '_status', 100)
                        
                        session_info_g = await asyncio.Task(redis_main.get, self.session_id+'_info')
                        
                        session_info = json.loads(session_info_g)
                        self.drone_veh_id = session_info['vehicle_id']
                        self.drone_api_key = session_info['api_key']
                        self.drone_ns = session_info['ns']

                        # return acknowledgement to customer
                        self.write("Command submitted succesfully")

                        # Submit the request to drone
                        self.ActionController = DroneRemoteAccess(self.drone_veh_id, self.drone_api_key, self.drone_ns)
                        print("RemoteAccess: Got the lock for 10 sec, performing action")
                        
                        #GFM success, resp = yield self.ActionController.attain_local_setpoint(self.sp_x, self.sp_y, self.sp_z,
                        #GFM                                                  self.sp_yaw, self.sp_yaw_valid )
                        success, resp = await self.ActionController.attain_local_setpoint(self.sp_x, self.sp_y, self.sp_z,
                                                                          self.sp_yaw, self.sp_yaw_valid )
                        
                        if success:
                            print("RemoteAccess: Remote Request success: ", resp)
                        else:
                            print("RemoteAccess: Remote Request failed: ", resp)

                        # keep the drone at that spot for next 10 seconds
                        await asyncio.sleep(10.)

                        # release the lock
                        await asyncio.Task(redis_main.set, self.session_id + '_status', 4)
                        
                        print("RemoteAccess: Released lock")
                        self.finish()
                    else:
                        print("RemoteAccess: session busy")
                        self.set_status(428, "session busy")
                        self.finish()
                else:
                    print("session not available")
                    self.set_status(401, "Wrong session ID")
                    self.finish()
            except (ValueError, KeyError) as error:
                print("session access request decode failed ", error)
                self.set_status(400, "unsupported input, JSON required")
                self.finish()
        else:
            self.set_status(400, "JSON input required")
            self.finish()


if __name__ == '__main__':
    # redis_main.flushall()
    redis_main.set("app_info", json.dumps({"status": 2}))  # set app not ready flag.

    drone_list = [{'api_key': '84d440b0ba95c19ccd8e56a2cf0e540694798850', 'vehicle_id': '6gi14TJq'},
                  {'api_key': '20fe4f04fe765cf265b81dbccd54a74303deba39', 'vehicle_id': '1atcQaG8', }]

    print("Init: Checking available drones")
    live_drones = confirm_drones(drone_list)

    redis_main.set("app_info", json.dumps({"status": 1}))  # Set 'app busy confirming drones' flag.
    print("Init: ", len(live_drones), " Drones ready, Connecting over WebSocket")

    ws_clients = []
    if len(live_drones) > 0:
        init_redis_structures(live_drones)
        for drone_info in live_drones:
            ws_clients.append(WebSocketClient(drone_info, None, sub_topics))
        for ws_client in ws_clients:
            ws_client.connect()
    else:
        print("No drone connected, Exit!")
        sys.exit(0)

    # update_drone_status()

    ### http server specific setup
    application = Application([
        (r"/", MainHandler),
        (r"/start_new_session", DroneSessionHandler),
        (r"/request_access", SessionAccessHandler)
    ])

    application.listen(8888)

    try:
        # ioloop.PeriodicCallback(update_drone_status, drone_status_update_rate, ioloop.IOLoop.instance()).start()
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        for ws_client in ws_clients:
            ws_client.stop_client()
        ioloop.IOLoop.instance().stop()
        ioloop.IOLoop.instance().close()
