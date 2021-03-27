"""
FLYTBASE INC grants Customer a perpetual, non-exclusive, royalty-free license to use this software.
 All copyrights, patent rights, and other intellectual property rights for this software are retained by FLYTBASE INC.
"""

from asyncio.tasks import wait
import json

# Change of the library for Tornado 6.1
#Giovanni Fonseca
import asyncio
import tornado.ioloop
from tornado import ioloop
from tornado.iostream import IOStream

from redis import Redis
# GFM from tornado import gen
from tornado.httpclient import AsyncHTTPClient

from gps_helper import get_offset_location, dist_ang_betn_coordinates


class SessionHandler(object):
    """
    Manage complete flight session.
    """

    def __init__(self, session_id, vehicle_id, api_key, namespace, name, poi, height, clearance, wait_time=10.,
                 url=None):
        self.session_id = session_id
        self.vehicle_id = vehicle_id
        self.api_key = api_key
        self.ns = namespace
        self.name = name
        self.poi = poi  # point of interest information. e.g. {'lat':45.,'long':65., 'alt':10.0}
        self.height = height  # height at which the drone should fly
        self.clearance = clearance  # distance away from PPOI
        self.wait_time = wait_time  # drone will wait at users;s location for these many seconds
        self.url = url  # stream endpoint

        # setup environment variables.
        self.api_base_url = 'https://dev.flytbase.com/rest/ros/' + self.ns
        self.header = {'Authorization': 'Token ' + self.api_key, 'VehicleID': self.vehicle_id}
        self.status = -1  # set session status flag to 'initilized state'
        self.fuse = True  # if fuse is false then the session will stay on hold. No call backs should execute.
        self.home = None
        self.target_loc = self.poi.copy()  # later change this to 'clearance' meter distance away from POI in straight line path.
        #  Initialize redis client
        self.redis = Redis(host='localhost')

        # instance of non blocking http client
        self.http_client = AsyncHTTPClient()
        self.init_redis_structs()

    # @gen.coroutine
    async def init_redis_structs(self):
        #  initialize session structure and upload to redis server. No need to update this later
        session_struct = json.dumps({"vehicle_id": self.vehicle_id, "session_key": "removed_key",
                                     "api_key": self.api_key, "ns": self.ns})
        #GFM yield gen.Task(self.redis.set, self.session_id + "_info", session_struct)
        await asyncio.Task(self.redis.set, self.session_id + "_info", session_struct)

        # initialize status structure for session on redis. This should be updated after state change.
        #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
        await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)



        #  update sessions structure. No need to update this.
        #GFM cur_sessions = yield gen.Task(self.redis.get, "sessions")
        cur_sessions = await asyncio.Task(self.redis.get, "sessions")
        try:
            cur_sessions = json.loads(cur_sessions)
            updated_sessions = cur_sessions.copy()
            updated_sessions[self.session_id] = {"session_key": "removed"}
            #GFM yield gen.Task(self.redis.set, "sessions", updated_sessions)
            await asyncio.Task(self.redis.set, "sessions", updated_sessions)
        except ValueError:
            print("session JSON decode error")

    #GFM @gen.coroutine
    async def run_mission(self):
        # todo "make sure app is initialized"
        #GFM yield gen.sleep(5.0)
        await asyncio.sleep(5.0)
        if self.status == -1 and self.fuse:
            print("Session Handler: Initialized, starting stream")
            #GFM success, resp = yield self.start_stream()
            success, resp = await self.start_stream()
            if success:
                print("Session Handler: Request success: ", resp)
            else:
                print("Session Handler: Request failed: ", resp)
            self.status = 0
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
        if self.status == 0 and self.fuse:
            # save home location.
            #GFM self.home = yield self.get_drone_state()
            self.home = await self.get_drone_state()

            # Update the target clearance distance away from POI
            offset_loc = get_offset_location(self.home['lat'], self.home['long'], self.poi['lat'], self.poi['long'],
                                             self.clearance)
            self.target_loc = {'lat': offset_loc[0], 'long': offset_loc[1], 'alt': self.poi['alt']}

            print("Session Handler: taking off")
            #GFM success, resp = yield self.take_off(3.0)
            success, resp = await self.take_off(3.0)
            if success:
                print("Request success: ", resp)
            else:
                print("Request failed: ", resp)
                # todo handle takeoff failure
            self.status = 1
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
        if self.status == 1 and self.fuse:
            print("Session Handler: Attaining mission height and correcting heading")
            # todo check that self.home is populated
            #GFM success, resp = yield self.attain_global_setpoint(self.home['lat'], self.home['long'], self.height, 3)
            success, resp = await self.attain_global_setpoint(self.home['lat'], self.home['long'], self.height, 3)
            if success:
                print("Session Handler: Request success: ", resp)
            else:
                print("Session Handler: Request failed: ", resp)
                # todo handle this case
            dist, ang = dist_ang_betn_coordinates(self.home['lat'], self.home['long'],
                                                  self.poi['lat'], self.poi['long'])
            delta_ang = ang - self.home['yaw']
            #GFM success, resp = yield self.attain_yaw_sp(delta_ang)
            success, resp = await self.attain_yaw_sp(delta_ang)
            if success:
                print("Session Handler: Request success: ", resp)
            else:
                print("Session Handler: Request failed: ", resp)
                # todo handle this case
            self.status = 2
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
        if self.status == 2 and self.fuse:
            print("Session Handler: Moving to goal")
            #GFM success, resp = yield self.attain_global_setpoint(self.target_loc['lat'], self.target_loc['long'],
            #                                                  self.height, 3)            
            success, resp = await self.attain_global_setpoint(self.target_loc['lat'], self.target_loc['long'],
                                                              self.height, 3)
            if success:
                print("Session Handler: Request success: ", resp)
            else:
                print("Session Handler: Request failed: ", resp)
            self.status = 3
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
        if self.status == 3 and self.fuse:
            # print "Session Handler: pointing towards user"
            # Nothing here
            self.status = 4
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
            # don't change mission number now, 4 will be used to allow 3rd party access.
        if self.status == 4 and self.fuse:
            print("Session Handler: Waiting at goal", self.wait_time)
            #GFM yield gen.sleep(self.wait_time)
            await asyncio.sleep(self.wait_time)
            print("Session Handler: confirming lock")
            #GFM access_lock = yield self.check_access_lock(4, 100)
            access_lock = await self.check_access_lock(4, 100)
            print("Session Handler: acquired lock")
            if not access_lock:
                print("FATAL!")
            self.status = 5
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
            # continue only if status code is 5 in database. If it is 100 (foreign access)
            # then wait for 10 more seconds before checking
        if self.status == 5 and self.fuse:
            print("Session Handler: Moving back to home")
            # success, resp = yield self.global_sp(self.home['lat'], self.home['long'], self.height, 0., False, False)
            #GFM success, resp = yield self.attain_global_setpoint(self.home['lat'], self.home['long'], self.height, 3)
            success, resp = await self.attain_global_setpoint(self.home['lat'], self.home['long'], self.height, 3)
            if success:
                print("Session Handler: Request success: ", resp)
            else:
                print("Session Handler: Request failed: ", resp)
            self.status = 6
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
        if self.status == 6 and self.fuse:
            print("Session Handler: landing")
            #success, resp = yield self.land()
            success, resp = await self.land()
            if success:
                print("Session Handler: Request success: ", resp)
            else:
                print("Session Handler: Request failed: ", resp)
            self.status = 7
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
        if self.status == 7 and self.fuse:
            print("Session Handler: stopping stream")
            #GFM success, resp = yield self.stop_stream()
            success, resp = await self.stop_stream()
            if success:
                print("Session Handler: Request success: ", resp)
            else:
                print("Session Handler: Request failed: ", resp)
            self.status = 8
            #GFM yield gen.Task(self.redis.set, self.session_id + "_status", self.status)
            await asyncio.Task(self.redis.set, self.session_id + "_status", self.status)
        # set_drone free
        #GFM yield self.close_session()
        await self.close_session()

    #GFM @gen.coroutine
    async def check_access_lock(self, wait_case, foreign_case):
        """return True when access lock is released"""
        # TOdo repeat only 3 times.
        #GFM current_state = yield gen.Task(self.redis.get, self.session_id + "_status")
        current_state = await asyncio.Task(self.redis.get, self.session_id + "_status")
        if current_state == str(wait_case):
            #GFM raise gen.Return(True)
            raise asyncio.Return(True)
        if current_state == str(foreign_case):
            print("Session Handler: will try to acquire lock again in 10 secs.")
            #GFM yield gen.sleep(10.)
            await asyncio.sleep(10.)
            #res = yield self.check_access_lock(wait_case, foreign_case)
            res = await self.check_access_lock(wait_case, foreign_case)
            #GFM raise gen.Return(res)
            raise asyncio.Return(res)

    #GFM @gen.coroutine
    async def attain_global_setpoint(self, lat, long, height, max_retries=3, max_error_retries=3, r_count=0, re_count=0):
        #GFM success, resp = yield self.global_sp(lat, long, height, 0., False, False)
        success, resp = await self.global_sp(lat, long, height, 0., False, False)
        if success:
            # print "Request success: ", resp
            max_error_retries = 0
            try:
                resp_dec = json.loads(resp)
                if not resp_dec['success']:
                    if r_count <= max_retries:
                        r_count += 1
                        print("Session Handler: Target not achieved, retrying: retry no. ", r_count)
                        success, resp = yield self.attain_global_setpoint(lat, long, height, max_retries,
                                                                          max_error_retries, r_count, re_count)
                        #GFM raise gen.Return((success, resp))
                        raise asyncio.Return((success, resp))
                    else:
                        #GFM raise gen.Return((False, resp))
                        raise asyncio.Return((False, resp))
                #GFM raise gen.Return((True, resp))
                raise asyncio.Return((True, resp))
            except ValueError:
                print("drone GPOS sp API json response decode failed", success, resp)
                #GFM raise gen.Return((False, resp))
                raise asyncio.Return((False, resp))
        else:
            max_retries = 0
            if re_count <= max_error_retries:
                print("Request failed, sending command again: retry no. ", re_count)
                re_count += 1
                #GFM success, resp = yield self.attain_global_setpoint(lat, long, height, max_retries, max_error_retries,
                #GFM                                                  r_count, re_count)
                success, resp = await self.attain_global_setpoint(lat, long, height, max_retries, max_error_retries,
                                                                  r_count, re_count)
                #GFM raise gen.Return((success, resp))
                raise asyncio.Return((success, resp))
            else:
                print("max error retries reached, sending last value")
                #GFM raise gen.Return((False, resp))
                raise asyncio.Return((False, resp))

    #GFM @gen.coroutine
    async def attain_yaw_sp(self, yaw_angle, max_retries=3, max_error_retries=3, r_count=0, re_count=0):
        #GFM success, resp = yield self.local_sp(x=0., y=0., z=0., yaw=yaw_angle, yaw_valid=True, relative=True)
        success, resp = await self.local_sp(x=0., y=0., z=0., yaw=yaw_angle, yaw_valid=True, relative=True)
        if success:
            max_error_retries = 0
            try:
                resp_dec = json.loads(resp)
                if not resp_dec['success']:
                    if r_count <= max_retries:
                        r_count += 1
                        print("Drone not reached target, sending pos set command again: retry no. ", r_count)
                        #GFM success, resp = yield self.yaw_sp(self, yaw_angle, max_retries=max_retries,
                        #GFM                                 max_error_retries=max_error_retries, r_count=0, re_count=0)
                        success, resp = await self.yaw_sp(self, yaw_angle, max_retries=max_retries,
                                                          max_error_retries=max_error_retries, r_count=0, re_count=0)
                        #GFM raise gen.Return((success, resp))
                        raise asyncio.Return((success, resp))
                    else:
                        #GFM raise gen.Return((False, resp))
                        raise asyncio.Return((False, resp))
                #GFM raise gen.Return((True, resp))
                raise asyncio.Return((True, resp))
            except ValueError:
                print("drone local sp API json response decode failed", success, resp)
                #GFM raise gen.Return((False, resp))
                raise asyncio.Return((False, resp))
        else:
            max_retries = 0
            if re_count <= max_error_retries:
                print("Request failed, sending command again: retry no. ", re_count)
                re_count += 1
                #GFM  success, resp = yield self.yaw_sp(self, yaw_angle, max_retries=max_retries,
                #                                  max_error_retries=max_error_retries, r_count=0, re_count=0)
                success, resp = await self.yaw_sp(self, yaw_angle, max_retries=max_retries,
                                                  max_error_retries=max_error_retries, r_count=0, re_count=0)
                #GFM raise gen.Return((success, resp))
                raise asyncio.Return((success, resp))
            else:
                print("max error retries reached, sending last value")
                #GFM raise gen.Return((False, resp))
                raise asyncio.Return((False, resp))

    #GFM @gen.coroutine
    async def get_drone_state(self):
        """fetch latest updated state"""
        #GFM gpos = yield gen.Task(self.redis.get, self.vehicle_id + '_gpos')
        gpos = await asyncio.Task(self.redis.get, self.vehicle_id + '_gpos')
        #GFM lpos = yield gen.Task(self.redis.get, self.vehicle_id + '_lpos')
        lpos = await asyncio.Task(self.redis.get, self.vehicle_id + '_lpos')
        #GFM batt = yield gen.Task(self.redis.get, self.vehicle_id + '_batt')
        batt = await asyncio.Task(self.redis.get, self.vehicle_id + '_batt')
        #GFM imu = yield gen.Task(self.redis.get, self.vehicle_id + '_imu')
        imu = await asyncio.Task(self.redis.get, self.vehicle_id + '_imu')
        try:
            gpos = json.loads(gpos)
            lpos = json.loads(lpos)
            batt = json.loads(batt)
            imu = json.loads(imu)
            drone_state = {"lat": gpos['lat'], "long": gpos['long'], "a_alt": gpos['alt'],
                           "alt": lpos['z'], 'batt': batt['percent'], 'yaw': imu['yaw']}
            #GFM raise gen.Return(drone_state)
            raise asyncio.Return(drone_state)
        except ValueError:
            print("JSON decode error drone live status, session")

    #GFM @gen.coroutine
    async def start_stream(self):
        url = self.api_base_url + '/video_streaming/start_raspicam_stream'
        body = json.dumps({'image_width': 0,
                           'image_height': 0,
                           'framerate': 0,
                           'brightness': 0,
                           'saturation': 0,
                           'flip': True,
                           'remote_url': self.url,
                           'remote_target': True,
                           'bitrate': 0})

        #GFM response = yield gen.Task(self.http_client.fetch, url, method='POST', headers=self.header,
        #                          body=body, request_timeout=180.0)
        response = await asyncio.Task(self.http_client.fetch, url, method='POST', headers=self.header,
                                  body=body, request_timeout=180.0)
        if response.error:
            #GFM raise gen.Return((False, response.error))
            raise asyncio.Return((False, response.error))
        else:
            #GFM raise gen.Return((True, response.body))
            raise asyncio.Return((True, response.body))

    #GFM @gen.coroutine
    async def stop_stream(self):
        url = self.api_base_url + '/video_streaming/stop_raspicam_stream'

        #GFM response = yield gen.Task(self.http_client.fetch, url, method='GET', headers=self.header, request_timeout=180.0)
        response = await asyncio.Task(self.http_client.fetch, url, method='GET', headers=self.header, request_timeout=180.0)

        if response.error:
            #GFM raise gen.Return((False, response.error))
            raise asyncio.Return((False, response.error))
        else:
            #GFM raise gen.Return((True, response.body))
            raise asyncio.Return((True, response.body))

    #GFM @gen.coroutine
    async def take_off(self, height):
        url = self.api_base_url + '/navigation/take_off'
        body = json.dumps({"takeoff_alt": height})

        #GFM response = yield gen.Task(self.http_client.fetch, url, method='POST', headers=self.header,
        #                          body=body, request_timeout=180.0)
        response = await asyncio.Task(self.http_client.fetch, url, method='POST', headers=self.header,
                                  body=body, request_timeout=180.0)
        if response.error:
            #GFM raise gen.Return((False, response.error))
            raise asyncio.Return((False, response.error))
        else:
            #GFM raise gen.Return((True, response.body))
            raise asyncio.Return((True, response.body))

    #GFM @gen.coroutine
    async def land(self):
        url = self.api_base_url + '/navigation/land'
        body = json.dumps({"async": False})

        #GFMresponse = yield gen.Task(self.http_client.fetch, url, method='POST', headers=self.header,
        #                          body=body, request_timeout=180.0)
        response = await asyncio.Task(self.http_client.fetch, url, method='POST', headers=self.header,
                                  body=body, request_timeout=180.0)
        if response.error:
            #GFM raise gen.Return((False, response.error))
            raise asyncio.Return((False, response.error))
        else:
            #GFM raise gen.Return((True, response.body))
            raise asyncio.Return((True, response.body))

    #GFM @gen.coroutine
    async def global_sp(self, lat, long, alt, yaw, yaw_valid, is_async):
        url = self.api_base_url + '/navigation/position_set_global'
        body = json.dumps({
            "lat_x": lat,
            "long_y": long,
            "rel_alt_z": alt,
            "yaw": yaw,
            "tolerance": 2.0,
            "async": is_async,
            "yaw_valid": yaw_valid
        })
        # print body, "wp sent to drone"
        #GFM response = yield gen.Task(self.http_client.fetch, url, method='POST', headers=self.header,
        #                          body=body, request_timeout=50.0)
        response = await asyncio.Task(self.http_client.fetch, url, method='POST', headers=self.header,
                                  body=body, request_timeout=50.0)
        if response.error:
            #GFM raise gen.Return((False, response.error))
            raise asyncio.Return((False, response.error))
        else:
            #raise gen.Return((True, response.body))
            raise asyncio.Return((True, response.body))

    #GFM @gen.coroutine
    async def local_sp(self, x, y, z, yaw, yaw_valid, relative):
        url = self.api_base_url + '/navigation/position_set'
        body = json.dumps({
            "x": x,
            "y": y,
            "z": z,
            "yaw": yaw,
            "yaw_valid": yaw_valid,
            "tolerance": 2.0,
            "relative": relative,
            "async": False,
            "body_frame": False

        })
        #GFM response = yield gen.Task(self.http_client.fetch, url, method='POST', headers=self.header,
        #                          body=body, request_timeout=50.0)
        response = await asyncio.Task(self.http_client.fetch, url, method='POST', headers=self.header,
                                  body=body, request_timeout=50.0)
        if response.error:
            #GFM raise gen.Return((False, response.error))
            raise asyncio.Return((False, response.error))
        else:
            #GFM raise gen.Return((True, response.body))
            raise asyncio.Return((True, response.body))

    #GFM @gen.coroutine
    async def close_session(self):
        print("Session Handler: Session complete, freeing the resources")
        #GFM yield gen.Task(self.redis.set, self.vehicle_id + '_status', 0)
        await asyncio.Task(self.redis.set, self.vehicle_id + '_status', 0)
