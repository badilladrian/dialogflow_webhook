import requests

data = {
    "drone_id": 2,
    "lat": 37.430069155325164,
    "lng": -122.0836991071701,
    "alt": 5
}

print(requests.post('http://localhost:8899/drone/1', json=data))