import json
import flask
import datetime
import os
from flask import request, jsonify, make_response
from help import AddDataToTable,AddRelativeDataTotable,getRelativeData,updatehealthstats,editby,deleteby
from flask_cors import CORS, cross_origin
import logging
import nltk
import requests
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

def finddata(email,query):
    text = nltk.word_tokenize(query)
    tagged=nltk.pos_tag(text)
    print(tagged)
    text=list(filter(lambda x: x[1] == 'NN' or x[1]=="JJ", tagged))
    for i in text:
        print(i[0])
        item,isname=getRelativeData(email,i[0])
        print(len(item))
        if(len(item)!= 0):
            return item[0],i[0],isname
    

def editdata(email,query):
    print(query)
    item,isname=getRelativeData(email,query)
    return item

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

@app.route("/api/FetchData",methods=["POST",])
def FetchData():
    user_id=None
    print(request.json)
    mac_address= request.json["mac_address"]
    health_stats={"heart_rate":request.json["heart_rate"],"glucose":request.json["glucose"],"geolocation":request.json["geolocation"],"blood_pressure":request.json["blood_pressure"]}
    print(health_stats)
    updatehealthstats(mac_address,health_stats)
    return make_response("",200)

# create a route for webhook
@app.route('/dialogflow-webhook', methods=['POST'])
def nanahealthbot():
    #get account details using ifd token
    response = requests.get("https://oauth2.googleapis.com/tokeninfo?id_token="+request.json["originalDetectIntentRequest"]["payload"]["user"]["idToken"])
    response=response.json()
    # print(request.json)
    #add user data at once  with name and email
    AddDataToTable(response["email"],response["name"])
    email=response["email"]
    #if user ask for adding new member
    if request.json["queryResult"]["intent"]["displayName"]=="OnBording":
        isreply=request.json["queryResult"]['parameters']["basic_reply"]
        if(isreply=='yes'):
            return {"followupEventInput":{"name":"yes","languageCode": "en-US"}}
        if(isreply=='no'):
            return {"followupEventInput":{"name":"no","languageCode": "en-US"}}
        else:
            return {"followupEventInput":{"name":"again","languageCode": "en-US"}}
    # if uer said yes to add new member
    if request.json["queryResult"]["intent"]["displayName"]=="OnBording - yes":
        print("i was here")
        name=request.json["queryResult"]['parameters']["name"]
        relation=request.json["queryResult"]['parameters']["relative"]
        print(name,relation,email)
        relative=AddRelativeDataTotable(email,name.lower(),relation.lower())
        if(relative!=None):
            print("added")
            return {"followupEventInput":{"name":"added","parameters":{
        "data":"i added {} as your {},do you wish to add more members?".format(name,relation),},"languageCode": "en-US"}}
        else:
            print("notadded")
            return {"followupEventInput":{"name":"notadded","parameters":{
        "data":"you alredy have {}as your {},do you wish to add another members?".format(name,relation),},"languageCode": "en-US"}}
    #if user relative is added to data  
    if request.json["queryResult"]["intent"]["displayName"]=="OnBording - yes - added":
        isreply=request.json["queryResult"]['parameters']["reply"]
        print(isreply)
        if(isreply=='yes'):
            return {"followupEventInput":{"name":"again","languageCode": "en-US"}}
        if(isreply=='no'):
            return {"followupEventInput":{"name":"no","languageCode": "en-US"}}
        else:
            return {"followupEventInput":{"name":"again","languageCode": "en-US"}}
    #if user relative  data already exist in DB
    if request.json["queryResult"]["intent"]["displayName"]=="OnBording - yes - notadded":
        isreply=request.json["queryResult"]['parameters']["reply"]
        print(isreply)
        if(isreply=='yes'):
            return {"followupEventInput":{"name":"again","languageCode": "en-US"}}
        if(isreply=='no'):
            return {"followupEventInput":{"name":"no","languageCode": "en-US"}}
        else:
            return {"followupEventInput":{"name":"again","languageCode": "en-US"}}
    # if user ask for blood_pressure
    if request.json["queryResult"]["intent"]["displayName"]=="health.blood_pressure":
        print("blood_pressure")
        text= request.json["queryResult"]["queryText"]
        data,rel,isname=finddata(email,text.lower())
        if data!=None and isname== True:
            return {'fulfillmentText':"{} blood_pressure is {}".format(rel,data["healthstats"]["blood_pressure"])}
        if data!=None and isname== False:
            return {'fulfillmentText':"your {} blood_pressure is {}".format(rel,data["healthstats"]["blood_pressure"])}
        else:
            return {'fulfillmentText': 'no data found.'}
    #if user ask for glucose
    if request.json["queryResult"]["intent"]["displayName"]=="health.glucose":
        text= request.json["queryResult"]["queryText"]
        data,rel,isname=finddata(email,text.lower())
        if data!=None and isname== True:
            return {'fulfillmentText':"{} glucose is {}".format(rel,data["healthstats"]["glucose"])}
        if data!=None and isname== False:
            return {'fulfillmentText':"your {} glucose is {}".format(rel,data["healthstats"]["glucose"])}
        else:
            return {'fulfillmentText': 'no data found.'}
    #if user ask for  heart rate
    if request.json["queryResult"]["intent"]["displayName"]=="health.heart_rate":
        text= request.json["queryResult"]["queryText"]
        data,rel,isname=finddata(email,text.lower())
        if data!=None and isname== True:
            return {'fulfillmentText':"{} heart_rate is {}".format(rel,data["healthstats"]["heart_rate"])}
        if data!=None and isname== False:
            return {'fulfillmentText':"your {} heart_rate is {}".format(rel,data["healthstats"]["heart_rate"])}
        else:
            return {'fulfillmentText': 'no data found.'}
    # ask for location
    if request.json["queryResult"]["intent"]["displayName"]=="health.location":
        text= request.json["queryResult"]["queryText"]
        data,rel,isname=finddata(email,text.lower())
        if data!=None and isname== True:
            return {'fulfillmentText':"{} location is at Longitude {} and latitude {}".format(rel,data["healthstats"]["geolocation"]["Lon"],data["healthstats"]["geolocation"]["Lat"])}
        if data!=None and isname== False:
            return {'fulfillmentText':"your {} location is at Longitude {} and latitude {}".format(rel,data["healthstats"]["geolocation"]["Lon"],data["healthstats"]["geolocation"]["Lat"])}
        else:
            return {'fulfillmentText': 'no data found.'}
    # if user ask for full state
    if request.json["queryResult"]["intent"]["displayName"]=="health.full_stats":
        text= request.json["queryResult"]["queryText"]
        data,rel,isname=finddata(email,text.lower())
        if data!=None and isname==True:
            return  {'fulfillmentText':"{} is feeling {}, BMP location is at Longitude {} and latitude {} glucose is {} ,blood_pressure is {}".format(data["username"],
            data["healthstats"]["blood_pressure"],data["healthstats"]["geolocation"]["Lon"],
            data["healthstats"]["geolocation"]["Lat"],data["healthstats"]["glucose"],data["healthstats"]["blood_pressure"])}
        if data!=None and isname== False:
            return  {'fulfillmentText':"{} is feeling {}, BMP location is at Longitude {} and latitude {}, glucose is {}, blood_pressure is {}".format(data["username"],
            data["healthstats"]["blood_pressure"],data["healthstats"]["geolocation"]["Lon"],
            data["healthstats"]["geolocation"]["Lat"],data["healthstats"]["glucose"],data["healthstats"]["blood_pressure"])}
        else:
            return{ 'fulfillmentText': 'no data found.'}
    # if user want to edit relative 
    if request.json["queryResult"]["intent"]["displayName"]=="EditRelative":
        try:
            text= request.json["queryResult"]['parameters']["name"]
            print("enter")
            data=editdata(email,text.lower())
            same=[]
            if len(data)==1:
                print("i was here")
                return  {"followupEventInput":{"name":"modify", "parameters": {
        "data":"{} is your {} do you wish to modify name or relation?".format(text,data[0]["relation"]),"key":"{}_{}".format(text,data[0]["relation"]) },"languageCode": "en-US"}}
            if len(data)>1:
                string=""
                key=""
                print("here")
                for i in data:
                    string=string+"{} is your {},".format(text,i["relation"])
                    key=key+"{}_{},".format(text,i["relation"])
                return  {"followupEventInput":{"name":"change", "parameters": {
        "data":string+"which one?","key":key },"languageCode": "en-US"}}
        except:
            return{ 'fulfillmentText': 'no data found.'}
    #if user select relative which he wants to edit and single relative with same name exist
    if request.json["queryResult"]["intent"]["displayName"]=="EditRelative - custom":
        text= request.json["queryResult"]['parameters']["type"]
        change=request.json["queryResult"]['parameters']["change"]["name"]
        key=request.json["queryResult"]["outputContexts"][5]["parameters"]["key"]
        print(text.lower(),change.lower(),key.lower())
        name,relation= editby(key.lower(),text.lower(),change.lower())
        return  {'fulfillmentText':"i Have added {}, as your {}".format(name,relation)}
    #if user select relative which he wants to edit  and multiple relative with same name exist
    if request.json["queryResult"]["intent"]["displayName"]=="EditRelative - custom-2":
        text= request.json["queryResult"]['parameters']["whom"]["name"]
        change=request.json["queryResult"]['parameters']["modify"]
        key=request.json["queryResult"]["outputContexts"][6]["parameters"]["key"]
        key=key.split(",")
        for i in key:
            if i.endswith(text):
                key1=i
        print(key1.lower())
        name,relation= editby(key1.lower())
        return  {'fulfillmentText':"i Have added {}, as your {}".format(name,relation)}
    #if user select relative which he wants to delete  and single relative with same name exist
    if request.json["queryResult"]["intent"]["displayName"]=="deleterelative - custom":
        text= request.json["queryResult"]['parameters']["sure"]
        key=request.json["queryResult"]["outputContexts"][7]["parameters"]["key"]
        print(text.lower())
        if text=="yes":
            deleteby(key.lower())
        return  {'fulfillmentText':"relation is deleted"}
    #if user req for delete relative
    if request.json["queryResult"]["intent"]["displayName"]=="deleterelative":
        try:
            text= request.json["queryResult"]['parameters']["whom"]
            print("enter")
            data=editdata(email,text.lower())
            same=[]
            if len(data)==1:
                print("i was here")
                return  {"followupEventInput":{"name":"delete", "parameters": {
        "data":"{} is your {} are you sure you want to remove this relation?".format(text,data[0]["relation"]),"key":"{}_{}".format(text,data[0]["relation"]) },"languageCode": "en-US"}}
            if len(data)>1:
                string=""
                key=""
                print("here")
                for i in data:
                    string=string+"{} is your {},".format(text,i["relation"])
                    key=key+"{}_{},".format(text,i["relation"])
                return  {"followupEventInput":{"name":"remove", "parameters": {
        "data":string+"which one?","key":key },"languageCode": "en-US"}}
        except:
            return{ 'fulfillmentText': 'no data found.'}
    #if user select relative which he wants to delete  and multiple relative with same name exist
    if request.json["queryResult"]["intent"]["displayName"]=="deleterelative - custom-2":
        text= request.json["queryResult"]['parameters']["whom"]["name"]
        key=request.json["queryResult"]["outputContexts"][7]["parameters"]["key"]
        key=key.split(",")
        for i in key:
            if i.endswith(text):
                key1=i
        print(key1.lower())
        deleteby(key1.lower())
        return  {'fulfillmentText':"relation is deleted"}
    return make_response("",200)
