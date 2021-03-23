"""
FLYTBASE INC grants Customer a perpetual, non-exclusive, royalty-free license to use this software.
 All copyrights, patent rights, and other intellectual property rights for this software are retained by FLYTBASE INC.
"""

from tornado import gen
from tornado import httpclient
from tornado import httputil
from tornado import websocket
from tornado import ioloop

import time
import functools
from functools import partial
import json
from redis import Redis, StrictRedis
from math import radians, cos, sin, asin, sqrt

""" helper classes """


class MsgStructs(object):
    def __init__(self, namespace, rate, id=2354):
        self.namespace = namespace
        self.rate = rate
        self.id = id

    def sub_msg(self, topic):
        if topic == 'gpos':
            return {"op": "subscribe", "topic": '/' + str(self.namespace) + '/mavros/global_position/global',
                    "id": self.id,
                    "type": 'sensor_msgs/NavSatFix', "throttle_rate": self.rate}
        if topic == 'lpos':
            return {"op": "subscribe", "topic": '/' + str(self.namespace) + '/mavros/local_position/local',
                    "id": self.id,
                    "type": 'geometry_msgs/TwistStamped', "throttle_rate": self.rate}
        if topic == 'imu':
            return {"op": "subscribe", "topic": '/' + str(self.namespace) + '/mavros/imu/data_euler',
                    "id": self.id,
                    "type": 'geometry_msgs/TwistStamped', "throttle_rate": self.rate}
        if topic == "battery":
            return {"op": "subscribe", "topic": '/' + str(self.namespace) + '/mavros/battery', "id": self.id,
                    "type": 'sensor_msgs/BatteryState', "throttle_rate": self.rate}
        return None

    def get_unsub_msg(self, topic):
        if topic == "gpos":
            return {"op": "unsubscribe", "topic": '/' + str(self.namespace) + '/mavros/global_position/global',
                    "id": self.id}
        if topic == "lpos":
            return {"op": "unsubscribe", "topic": '/' + str(self.namespace) + '/mavros/local_position/local',
                    "id": self.id}
        if topic == "imu":
            return {"op": "unsubscribe", "topic": '/' + str(self.namespace) + '/mavros/imu/data_euler',
                    "id": self.id}
        if topic == "battery":
            return {"op": "unsubscribe", "topic": '/' + str(self.namespace) + '/mavros/battery', "id": self.id}
        return None


class WebSocketClientBase(object):
    """Base class for websocket client
    """

    def __init__(self):
        self.connect_timeout = 60
        self.request_timeout = 60

    def connect(self):
        """Connect to the server.
        """
        url = 'wss://dev.flytbase.com/websocket'
        headers = httputil.HTTPHeaders(
            {'Content-Type': 'application/json', 'Authorization': 'Token ' + str(self.api_key),
             'VehicleID': str(self.vehicle_id)})
        request = httpclient.HTTPRequest(url=url,
                                         connect_timeout=self.connect_timeout,
                                         request_timeout=self.request_timeout,
                                         headers=headers)
        ws_conn = websocket.WebSocketClientConnection(ioloop.IOLoop.current(),
                                                      request)
        ws_conn.connect_future.add_done_callback(self._connect_callback)

    def send(self, data):
        """Send message to the server
        :param str data: message.
        """
        if not self._ws_connection:
            raise RuntimeError('Web socket connection is closed.')
        self._ws_connection.write_message(data)

    def close(self):
        """Close connection.
        """
        if not self._ws_connection:
            raise RuntimeError('Web socket connection is already closed.')

        self._ws_connection.close()

    def _connect_callback(self, future):
        if future.exception() is None:
            self._ws_connection = future.result()
            self._on_connection_success()
            self._read_messages()
        else:
            self._on_connection_error(future.exception())

    @gen.coroutine
    def _read_messages(self):
        while True:
            msg = yield self._ws_connection.read_message()
            if msg is None:
                self._on_connection_close()
                break
            self._on_message(msg)

    def _on_message(self, msg):
        """
        Override this method
        This is called when new message is available from the server.
        :param str msg: server message.
        """
        pass

    def _on_connection_success(self):
        """
        Override this method
        This is called on successful connection ot the server.
        """
        pass

    def _on_connection_close(self):
        """
        Override this method
        This is called when server closed the connection.
        """
        pass

    def _on_connection_error(self, exception):
        """
        Override this method
        This is called in case if connection to the server could
        not established.
        """
        pass


class WebSocketClient(WebSocketClientBase):
    def __init__(self, drone_info, drone_vec, sub_topics, throttle_rate=6000):
        self.api_key = drone_info["api_key"]  # API key to talk with drone.
        self.vehicle_id = drone_info["vehicle_id"]  # vehicle ID of the drone.
        self.namespace = drone_info["namespace"]  # namespace of the drone
        self.topics_subscribed = []
        self.drone_vec = drone_vec  # drone status vector that will be updated.
        self.topics_to_subscribe = sub_topics
        self.msglib = MsgStructs(self.namespace, throttle_rate)
        self.redis = StrictRedis(host='localhost')
        super(WebSocketClient, self).__init__()

    def _on_message(self, msg):
        try:
            res = json.loads(msg)
            ioloop.IOLoop.instance().add_callback(partial(self.parse_msg, res))
        except ValueError:
            print("json decoding failed")

    def _on_connection_success(self):
        print('Drone Connected! ', self.vehicle_id)
        deadline = time.time() + 1
        ioloop.IOLoop().instance().add_timeout(deadline, functools.partial(self.subscribe_to_topics))

    def _on_connection_close(self):
        print('Connection closed!')

    def _on_connection_error(self, exception):
        print('Connection error: %s', exception)

    def subscribe_to_topics(self):
        for topic in self.topics_to_subscribe:
            self.topics_subscribed.append(topic)
            ioloop.IOLoop.instance().add_callback(partial(self.send, json.dumps(self.msglib.sub_msg(topic))))
            # TODO remove debug statement
            # ioloop.IOLoop().instance().add_timeout(time.time()+10, functools.partial(self.stop_client))

    def stop_client(self):
        #  unsubscribe from the data.
        for topic in self.topics_subscribed:
            self.send(json.dumps(self.msglib.get_unsub_msg(topic)))
        # call close method
        self.close()

    def parse_msg(self, msg):
        if isinstance(msg, dict):
            if 'op' in msg.keys():
                if msg['op'] == 'publish':
                    # print msg
                    word6 = msg['topic'][-6:]
                    if word6 == "global":
                        lat = msg['msg']['latitude']
                        lon = msg['msg']['longitude']
                        alt = msg['msg']['altitude']
                        # print lat, lon, "global"
                        self.redis.set(self.vehicle_id + '_gpos', json.dumps({"lat": lat, "long": lon, "alt": alt}))
                    if word6 == "/local":
                        x = msg['msg']['twist']['linear']['x']
                        y = msg['msg']['twist']['linear']['y']
                        z = msg['msg']['twist']['linear']['z']
                        yaw = msg['msg']['twist']['angular']['z']
                        # print x,y,z, "local"
                        self.redis.set(self.vehicle_id + '_lpos', json.dumps({"x": x, "y": y, "z": z, "yaw": yaw}))
                    if word6 == "attery":
                        percent = msg['msg']['percentage']
                        # print percent*100, " % battery"
                        self.redis.set(self.vehicle_id + '_batt', json.dumps({"percent": percent}))
                    if word6 == "_euler":
                        yaw = msg['msg']['twist']['linear']['z']
                        # print percent*100, " % battery"
                        self.redis.set(self.vehicle_id + '_imu', json.dumps({"yaw": yaw}))


def dist_bet_coordinates(lon1, lat1, lon2, lat2):
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


class DroneRemoteAccess(object):

    def __init__(self, vehicle_id, api_key, ns):
        self.vehicle_id = vehicle_id
        self.api_key = api_key
        self.ns = ns

        # setup environment variables.
        self.api_base_url = 'https://dev.flytbase.com/rest/ros/' + self.ns
        self.header = {'Authorization': 'Token ' + self.api_key, 'VehicleID': self.vehicle_id}
        # instance of non blocking http client
        self.http_client = httpclient.AsyncHTTPClient()

    @gen.coroutine
    def local_sp(self, x, y, z, yaw, yaw_valid, relative):
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
        response = yield gen.Task(self.http_client.fetch, url, method='POST', headers=self.header,
                                  body=body, request_timeout=50.0)
        if response.error:
            raise gen.Return((False, response.error))
        else:
            raise gen.Return((True, response.body))

    @gen.coroutine
    def attain_local_setpoint(self, x, y, z, yaw, yaw_valid, max_error_retries=3, re_count=0):
        success, resp = yield self.local_sp(x,y,z,yaw,yaw_valid,True)
        if not success:
            if re_count <= max_error_retries:
                print("Request failed, sending command again: retry no. ", re_count)
                re_count += 1
                success, resp = yield self.local_sp(x,y,z,yaw,yaw_valid,True,max_error_retries,re_count)
                raise gen.Return((success, resp))
            else:
                print("max error retries reached, sending last value")
                raise gen.Return((False, resp))
        else:
            raise gen.Return((True, resp))

