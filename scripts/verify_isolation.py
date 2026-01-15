import sys
import os
import requests
sys.path.append(os.getcwd())
from core.config import settings

BASE_URL = "http://localhost:8000/api/v1"

def test_isolation():
    print("--- TESTING ISOLATION (RBAC) ---")
    
    # 1. Try to access messages without ANY token
    print("\n[TEST] Access /messages (No Token)")
    try:
        # Poking Org 1
        res = requests.get(f"{BASE_URL}/messages?org_id=1&limit=1")
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            count = len(res.json().get('hits', []))
            print(f"CRITICAL: Accessed {count} messages without auth!")
        else:
            print("PASS: Access denied.")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Try to access Admin Orgs without token
    print("\n[TEST] Access /admin/organizations (No Token)")
    try:
        res = requests.get(f"{BASE_URL}/admin/organizations")
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print(f"CRITICAL: Extracted Organization list: {len(res.json())} orgs found.")
        else:
            print("PASS: Access denied.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_isolation()
