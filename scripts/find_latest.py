import requests
import json
import time

URL = "http://localhost:8000/api/v1/messages"
resp = requests.get(URL, params={"q": "Welcome", "limit": 1, "org_id": 13})
try:
    hits = resp.json().get('hits', [])
    if hits:
        print(hits[0]['id'])
    else:
        print("No hits")
except Exception as e:
    print(e)
