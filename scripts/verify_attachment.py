import requests
import json

ID = "f5d03ee4-bd32-435d-9ddc-234194273cd6"
URL = "http://localhost:8000/api/v1/messages"
resp = requests.get(URL, params={"q": "Test Email with Attachment", "limit": 100, "org_id": 13})

found = False
if resp.status_code == 200:
    hits = resp.json().get('hits', [])
    for h in hits:
        if h['id'] == ID:
            found = True
            print(f"MATCH FOUND: {h['id']}")
            print(f"Has Attachments: {h.get('has_attachments')}")
            print(f"CV Attachments: {h.get('cv_attachments')}")
            break

if not found:
    print("Message not found in top 100 hits.")
    # Debug: print all IDs found
    print(f"IDs found: {[h['id'] for h in hits]}")
