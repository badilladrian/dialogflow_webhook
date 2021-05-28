import json
import flask
import datetime
import os
from flask import request, jsonify, make_response
from flask_cors import CORS, cross_origin
import logging

logger = logging.getLogger(__name__)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = flask.Flask(__name__)

config = {
    "DEBUG": True,
    "JSON_SORT_KEYS": False
}

app.config.from_mapping(config)
cors = CORS(app)

app.config['CORS_HEADERS'] = 'Content-Type'


@app.route('/', methods=['GET'])
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def ping():
    response = jsonify('Im active!')
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


def results():
    response_data = {
        "introduction": "Hello Sir",
        "asking_family_member": "How many member do you want",
        "asking_health_stats": "Please wait sir, we're fetching data"
    }
    req = request.get_json(force=True)
    action = req.get('queryResult').get('action')
    print(response_data.keys())
    print(action in response_data.keys())
    return ({"data": response_data[action]}, 200) if action in response_data.keys() else (
    {"data": "Sorry for now we've no service for that"}, 404)


# create a route for webhook
@app.route('/dialogflow-webhook', methods=['POST'])
def webhook():
    # return response
    response, status = results()
    return make_response(jsonify(response)), status