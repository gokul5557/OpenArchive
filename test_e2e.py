import smtplib
from email.message import EmailMessage
import time
import requests
import sys

def send_mail():
    msg = EmailMessage()
    msg.set_content("This is a test email body for OpenArchive verification.")
    msg['Subject'] = "Verification Test Email"
    msg['From'] = "me@example.com"
    msg['To'] = "archive@example.com"

    try:
        with smtplib.SMTP('localhost', 2525) as s:
            s.send_message(msg)
        print("[TEST] Email sent successfully.")
    except Exception as e:
        print(f"[TEST] Failed to send email: {e}")
        sys.exit(1)

def verify_api():
    base_url = "http://localhost:8000/api/v1"
    headers = {"X-API-Key": "secret"} # Verify API Key usage if needed, though Get doesn't require it in my code (oops, check main.py)
    
    # main.py does NOT require API Key for GET, only for POST sync. Good.
    
    print("[TEST] Waiting for sync (10s)...")
    time.sleep(10)
    
    try:
        # Search
        res = requests.get(f"{base_url}/messages?q=Verification", headers=headers)
        data = res.json()
        print(f"[TEST] Search Result: {data}")
        
        if not data.get('hits'):
            print("[TEST] FAIL: No hits found.")
            sys.exit(1)
            
        msg_id = data['hits'][0]['id']
        print(f"[TEST] Found Message ID: {msg_id}")
        
        # Retrieve
        res = requests.get(f"{base_url}/messages/{msg_id}")
        msg_data = res.json()
        print(f"[TEST] Retrieve Result: {msg_data}")
        
        if "This is a test email body" in msg_data.get('content', ''):
             print("[TEST] SUCCESS: Content matches!")
        else:
             print("[TEST] FAIL: Content mismatch.")
             sys.exit(1)
             
    except Exception as e:
        print(f"[TEST] API Verification Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send_mail()
    verify_api()
