# To run the application

Until we run the application, we have to install the Redis Client (the server is included) in our PC (this different from
the redis requirement in the requirements.txt file).

https://github.com/rgl/redis/downloads

Then you choose the latest version, then you have to follow the instructions and install it. When it's installed, you have to run
the server. For that, you need to find the path and then run the file

```
redis.server.exe 
```

In most cases, the file is under 

```
C:\Program Files\Redis\redis-server.exe
```
After that, you can simply follow the next steps:

```
cd safewrd/finder_app
python main_activity.py
```

Wait for the app to initialize and drones to be connected. If no drones from the list are available
then app will gracefully shutdown.


Creating a new session/mission:

```
python test_script.py
(this will return a session id), e.g, S0015168190028796
```

Trying remote access during active session/mission:
i. this will work only when drone is waiting at POI location,
ii. only one request will be served at a time.
iii. Each request will keep the drone access locked for 10 sec after command execution.
     During this time no other request will be entertained.
iv. Send session ID as argument for following test script.

```
python test_remote_access.py S0015168190028796
```