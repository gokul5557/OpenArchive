import requests
import json
import random
import uuid
import base64
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

API_URL = "http://127.0.0.1:8000/api/v1/sync"
ADMIN_URL = "http://127.0.0.1:8000/api/v1/admin"
import os
API_KEY = os.getenv("CORE_API_KEY", "secret")

DOMAINS = ["gmail.com", "sagasofthub.com"]
NUM_USERS_PER_DOMAIN = 100
TOTAL_MESSAGES = 100000
BATCH_SIZE = 200 # Reduced for stability
NUM_THREADS = 4  # Aligned with 4 cores

# Templates for Enron-like emails
SUBJECTS = [
    "Re: Enron North America Corp.", "Schedule for tomorrow", "Energy Trading Update",
    "Meeting regarding project Alpha", "CONFIDENTIAL: Quarterly Report",
    "Legal Review - Contract #9928", "RE: Lunch today?", "California Power Grid Status",
    "Compliance Training Reminder", "Draft proposal for deregulation"
]

BODIES = [
    "I have reviewed the documents and they look good to go. Please proceed with the filing.",
    "Can we meet at 10 AM tomorrow to discuss the trading strategy?",
    "The market is moving fast. We need to adjust our positions by EOD.",
    "Attached is the latest draft of the agreement. Let me know if you have any comments.",
    "Please ensure all compliance protocols are followed for the next trade.",
    "We need to stay ahead of the regulatory changes in California.",
    "Thank you for the update. I will circle back with the team.",
    "Is the reporting system back online? I need to pull the numbers for the audit.",
    "The legal team has approved the move. We are clear to close.",
    "Great work on the project. Let's keep the momentum going."
]

progress_lock = threading.Lock()
messages_pushed = 0

def create_users():
    print("Verifying users...", flush=True)
    users = []
    for domain in DOMAINS:
        for i in range(NUM_USERS_PER_DOMAIN):
            username = f"user_{i}_{domain.split('.')[0]}"
            email = f"{username}@{domain}"
            users.append(email)
            try:
                requests.post(f"{ADMIN_URL}/users", json={
                    "username": email, "role": "auditor", "domains": [domain]
                }, timeout=5)
            except:
                pass 
    print(f"Total Users ready: {len(users)}", flush=True)
    return users

def push_batch(batch_num, users, fernet_key, cipher):
    global messages_pushed
    batch = []
    for _ in range(BATCH_SIZE):
        mid = str(uuid.uuid4())
        sender = random.choice(users)
        recipient = random.choice(users)
        subject = random.choice(SUBJECTS)
        body = random.choice(BODIES)
        
        metadata = {
            "from": sender, "to": recipient, "subject": subject,
            "date": int((datetime.now() - timedelta(days=random.randint(0, 365))).timestamp()),
            "size": len(body), "has_attachments": random.choice([True, False]),
            "is_spam": random.choice([False, False, False, True]) 
        }
        
        blob_enc = cipher.encrypt(body.encode())
        blob_b64 = base64.b64encode(blob_enc).decode('utf-8')
        
        batch.append({
            "id": mid, "key": fernet_key, "metadata": metadata, "blob_b64": blob_b64
        })
        
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.post(API_URL, headers={"X-API-Key": API_KEY}, json={"batch": batch}, timeout=120)
            if res.status_code == 200:
                with progress_lock:
                    messages_pushed += BATCH_SIZE
                    if messages_pushed % 2000 == 0:
                        print(f"Progress: {messages_pushed}/{TOTAL_MESSAGES}", flush=True)
                return
            else:
                print(f"Batch {batch_num} attempt {attempt+1} failed: {res.status_code}", flush=True)
        except Exception as e:
            print(f"Batch {batch_num} attempt {attempt+1} error: {e}", flush=True)
        time.sleep(1)

def generate_and_push_parallel(users):
    print(f"Generating and pushing {TOTAL_MESSAGES} messages using {NUM_THREADS} threads...", flush=True)
    fernet_key = Fernet.generate_key().decode()
    cipher = Fernet(fernet_key.encode())
    total_batches = TOTAL_MESSAGES // BATCH_SIZE
    
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        for i in range(total_batches):
            executor.submit(push_batch, i, users, fernet_key, cipher)

if __name__ == "__main__":
    users = create_users()
    generate_and_push_parallel(users)
    print("Ingestion complete.", flush=True)
