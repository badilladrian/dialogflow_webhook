import pymongo

def GetConnection():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")

    mydb = myclient["mydatabase"]
    return mydb