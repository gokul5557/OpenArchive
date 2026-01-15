import requests
import pyotp
import sys
import os

sys.path.append(os.getcwd())
from core.config import settings

BASE_URL = "http://localhost:8000/api/v1"

def test_2fa_flow():
    print("--- TESTING 2FA FLOW ---")
    
    # 1. Login (Should succeed without 2FA initially)
    print("\n[TEST] 1. Initial Login (No 2FA)")
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin"})
        if res.status_code == 200:
            token = res.json()['access_token']
            headers = {"Authorization": f"Bearer {token}"}
            print("PASS: Logged in successfully.")
        else:
            print(f"FAIL: Login failed: {res.text}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return

    # 2. Setup 2FA
    print("\n[TEST] 2. Setup 2FA")
    secret = None
    try:
        res = requests.post(f"{BASE_URL}/auth/2fa/setup", headers=headers)
        if res.status_code == 200:
            data = res.json()
            secret = data['secret']
            print(f"PASS: Got secret: {secret}")
        else:
            print(f"FAIL: Setup failed: {res.text}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return

    # 3. Enable 2FA
    print("\n[TEST] 3. Enable 2FA")
    totp = pyotp.TOTP(secret)
    code = totp.now()
    try:
        res = requests.post(f"{BASE_URL}/auth/2fa/enable", headers=headers, json={"secret": secret, "code": code})
        if res.status_code == 200:
            print("PASS: 2FA Enabled.")
        else:
            print(f"FAIL: Enable failed: {res.text}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return

    # 4. Login without OTP (Should Fail)
    print("\n[TEST] 4. Login without OTP (Should Fail)")
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin"})
        if res.status_code == 401:
            if "2FA Required" in res.text:
                print("PASS: Login rejected (2FA Required).")
            else:
                print(f"FAIL: Login rejected but wrong message: {res.text}")
        else:
            print(f"FAIL: Login succeeded unexpectedy: {res.status_code}")
    except Exception as e:
        print(f"Error: {e}")

    # 5. Login with OTP (Should Succeed)
    print("\n[TEST] 5. Login with OTP")
    code = totp.now()
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin", "otp": code})
        if res.status_code == 200:
            print("PASS: Logged in with 2FA.")
        else:
            print(f"FAIL: Login with 2FA failed: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_2fa_flow()
