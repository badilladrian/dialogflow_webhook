from .Config import GetConnection
import pymongo

def AddDataToTable(email_id=None,user_name=None):
    try:
        db = GetConnection()
        mydoc = db["safeWrdUserTable"]
        Item={
            '_id': email_id,
            'user_name': user_name,
            }
        x = mydoc.insert_one(Item)
        print(x)
        return x
    except pymongo.errors.DuplicateKeyError:
        pass

def AddRelativeDataTotable(user_email_id=None,user_name=None,relation=None,healthstats=None,mac_address=None):
    try:
        db = GetConnection()
        mydoc = db["RelativeTable"]
        Item={
            '_id':user_name+"_"+relation,
            'email_id': user_email_id,
            'username': user_name,
            'relation': relation,
            'healthstats':healthstats,
            'macAddress':4567
            }
        x = mydoc.insert_one(Item)
        print(x,"data added")
        return x
    except pymongo.errors.DuplicateKeyError:
        return None
def updatehealthstats(mac_Address=None,healthstats=None):
    try:
        db = GetConnection()
        mydoc = db["RelativeTable"]
        myquery = { "macAddress": 4567 }
        newvalues = { "$set": { 'healthstats':healthstats } }
        mydoc.update_one(myquery, newvalues)
        for x in mydoc.find():
            print(x)
        return "done"
    except pymongo.errors.DuplicateKeyError:
        return None
def deleteby(key):
    try:
        db = GetConnection()
        mydoc = db["RelativeTable"]
        myquery = { "_id":key }
        mydoc.delete_one(myquery)
        return "done"
    except pymongo.errors.DuplicateKeyError:
        return None
def editby(key,dtype,modify):
    try:
        db = GetConnection()
        mydoc = db["RelativeTable"]
        if dtype=="name":
            for x in mydoc.find():
                print(x)
            myquery = { "_id":key }
            x= list(mydoc.find(myquery))
            print(x)
            Item={
            '_id':modify+"_"+x[0]["relation"],
            'email_id': x[0]["email_id"],
            'username': modify,
            'relation': x[0]["relation"],
            'healthstats':x[0]["healthstats"],
            'macAddress':x[0]["macAddress"]
            }
            mydoc.insert_one(Item)
            mydoc.delete_one(myquery)
            return modify,x[0]["relation"]

        else:
            myquery = { "_id":key }
            newvalues = { "$set": { 'username':modify } }
            x= list(mydoc.find(myquery))
            print(x)
            Item={
            '_id':x[0]["username"]+"_"+modify,
            'email_id': x[0]["email_id"],
            'username': x[0]["username"],
            'relation': modify,
            'healthstats':x[0]["healthstats"],
            'macAddress':x[0]["macAddress"]
            }
            mydoc.insert_one(Item)
            mydoc.delete_one(myquery)
            return x[0]["username"],modify
    except pymongo.errors.DuplicateKeyError:
        return None

def getRelativeData(user_email_id,querydata):
    db = GetConnection()
    mydoc = db["RelativeTable"]
    myquery = { "email_id": user_email_id,"username":querydata }
    data = list(mydoc.find(myquery))
    isname= True
    print(len(data))
    if len(data)!=0:
        print("enter2")
        return data,isname
    if(len(data)==0):
        print("enter here")
        myquery = { "email_id": user_email_id,"relation":querydata }
        data = list(mydoc.find(myquery))
        if len(data)!=0:
            isname= False
            return data,isname
    else:
        return "",None
    # except:
    #     print("error")
    
