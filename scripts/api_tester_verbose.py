import requests
import json
import uuid
import sys
import time
import smtplib
from email.message import EmailMessage

BASE_URL = "http://localhost:8000/api/v1"

# ANSI colors for better output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

def log_success(msg):
    print(f"{Colors.OKGREEN}⠿ SUCCESS: {msg}{Colors.ENDC}")

def log_fail(msg, detail=None):
    print(f"{Colors.FAIL}✘ FAILED: {msg}{Colors.ENDC}")
    if detail:
        print(f"  Detail: {detail}")

def log_info(msg):
    print(f"{Colors.OKBLUE}ℹ {msg}{Colors.ENDC}")

def log_http(method, url, payload=None, response=None):
    print(f"\n{Colors.CYAN}{Colors.BOLD}>>> {method} {url}{Colors.ENDC}")
    if payload:
        print(f"{Colors.CYAN}Request Payload:{Colors.ENDC}\n{json.dumps(payload, indent=2)}")
    if response is not None:
        status_color = Colors.OKGREEN if response.status_code < 400 else Colors.FAIL
        print(f"{status_color}<<< Status: {response.status_code}{Colors.ENDC}")
        try:
            print(f"{Colors.CYAN}Response Body:{Colors.ENDC}\n{json.dumps(response.json(), indent=2)}")
        except:
            print(f"{Colors.CYAN}Response Body:{Colors.ENDC}\n{response.text}")
    print("-" * 40)

def send_test_email(to_domain):
    log_info(f"Sending test email to {to_domain}...")
    msg = EmailMessage()
    msg.set_content("Hello, this is an automated test email with PII data. SSN: 000-00-0000. Keyword: SECURE_VAULT.")
    msg['Subject'] = 'Automated API Test Message'
    msg['From'] = 'tester@external.com'
    msg['To'] = f'audit@{to_domain}'

    try:
        with smtplib.SMTP('localhost', 2525) as s:
            s.send_message(msg)
        log_success("Test email sent via SMTP")
        return True
    except Exception as e:
        log_fail("Send test email", str(e))
        return False

def test_organizations():
    log_info("Testing Organizations...")
    org_slug = f"test-org-{uuid.uuid4().hex[:6]}"
    
    # 1. Create
    payload = {
        "name": "Tester Org",
        "slug": org_slug,
        "domains": ["tester-labs.xyz"]
    }
    url = f"{BASE_URL}/admin/organizations"
    res = requests.post(url, json=payload)
    log_http("POST", url, payload, res)
    
    if res.status_code == 200:
        org_id = res.json().get("id")
        log_success(f"Created Org ID: {org_id}")
    else:
        log_fail("Create Org", res.text)
        return None

    # 2. List
    url = f"{BASE_URL}/admin/organizations"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        orgs = res.json()
        if any(o['id'] == org_id for o in orgs):
            log_success("Org found in list")
        else:
            log_fail("Org not found in list")
    else:
        log_fail("List Orgs", res.text)

    return org_id

def test_users(org_id):
    log_info("Testing Users...")
    username = f"test-user-{uuid.uuid4().hex[:6]}"
    
    # 1. Create
    payload = {
        "username": username,
        "password": "hashed_password_placeholder",
        "role": "client_admin",
        "org_id": org_id
    }
    url = f"{BASE_URL}/admin/users"
    res = requests.post(url, json=payload)
    log_http("POST", url, payload, res)
    if res.status_code == 200:
        user_id = res.json().get("id")
        log_success(f"Created User: {username} (ID: {user_id})")
    else:
        log_fail("Create User", res.text)
        return None

    # 2. List
    url = f"{BASE_URL}/admin/users?org_id={org_id}"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        users = res.json()
        if any(u['username'] == username for u in users):
            log_success("User found in list")
        else:
            log_fail("User not found in list")
    else:
        log_fail("List Users", res.text)

    return user_id

def test_audit_logs(org_id):
    log_info("Testing Audit Logs & Fidelity...")
    
    # 1. Create Log
    payload = {
        "username": "tester",
        "action": "API_INTEGRITY_TEST",
        "details": {"test_run_id": uuid.uuid4().hex}
    }
    url = f"{BASE_URL}/admin/audit-logs?org_id={org_id}"
    res = requests.post(url, json=payload)
    log_http("POST", url, payload, res)
    if res.status_code == 200:
        log_success(f"Log generated. Hash: {res.json().get('hash')[:20]}...")
    else:
        log_fail("Create Audit Log", res.text)

    # 2. Verify Chain
    url = f"{BASE_URL}/admin/audit-logs/verify?org_id={org_id}"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        data = res.json()
        if data.get("valid"):
            log_success(f"Audit Chain Valid. Count: {data.get('log_count')}")
        else:
            log_fail("Audit chain integrity failure", data.get("error"))
    else:
        log_fail("Verify Audit Logs", res.text)

def test_messages(org_id):
    log_info("Testing Messages & PII...")
    # Wait for ingestion if we just sent an email
    time.sleep(3)
    
    url = f"{BASE_URL}/messages?org_id={org_id}&limit=1"
    res = requests.get(url)
    log_http("GET", url, None, res)
    hits = res.json().get("hits", [])
    
    if not hits:
        log_info("No messages in new org. Falling back to Org 13 for metadata tests.")
        url = f"{BASE_URL}/messages?org_id=13&limit=1"
        res = requests.get(url)
        log_http("GET", url, None, res)
        hits = res.json().get("hits", [])
        active_org = 13
    else:
        active_org = org_id

    if not hits:
        log_fail("No messages found to test metadata endpoints.")
        return None
    
    msg_id = hits[0]['id']
    log_success(f"Retrieved MSG ID: {msg_id} (Org: {active_org})")

    # 1. Detail
    url = f"{BASE_URL}/messages/{msg_id}?org_id={active_org}"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        log_success("GET Message Content: OK")
    else:
        log_fail("GET Message Content", res.text)

    # 2. PII Scan
    url = f"{BASE_URL}/messages/{msg_id}/pii-scan?org_id={active_org}"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        data = res.json()
        log_success(f"PII Scan: OK (Detected: {len(data.get('entities', []))})")
    else:
        log_fail("PII Scan", res.text)

    # 3. Redaction Preview
    url = f"{BASE_URL}/messages/{msg_id}/preview-redacted?org_id={active_org}"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        log_success("Redaction Preview: OK")
    else:
        log_fail("Redaction Preview", res.text)

    # 4. Headers
    url = f"{BASE_URL}/messages/{msg_id}/headers?org_id={active_org}"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        log_success(f"Headers retrieved: {len(res.json())}")
    else:
        log_fail("Get Headers", res.text)

    return msg_id, active_org

def test_legal_holds(org_id):
    log_info("Testing Legal Holds...")
    hold_name = f"Litigation-Hold-{uuid.uuid4().hex[:4]}"
    
    # 1. Create Hold
    payload = {
        "name": hold_name,
        "reason": "API Tester Validation",
        "filter_criteria": {"from": "tester@domain.com", "q": "SECURE_VAULT"}
    }
    url = f"{BASE_URL}/admin/holds?org_id={org_id}"
    res = requests.post(url, json=payload)
    log_http("POST", url, payload, res)
    if res.status_code == 200:
        hold_id = res.json().get("id")
        log_success(f"Created Hold: {hold_name} (ID: {hold_id})")
    else:
        log_fail("Create Hold", res.text)
        return None

    return hold_id

def test_cases(org_id, msg_id):
    log_info("Testing Cases...")
    case_name = f"Investigation-{uuid.uuid4().hex[:4]}"
    
    # 1. Create
    payload = {
        "name": case_name,
        "description": "API Test Case",
        "org_id": org_id
    }
    url = f"{BASE_URL}/cases?org_id={org_id}"
    res = requests.post(url, json=payload)
    log_http("POST", url, payload, res)
    if res.status_code == 200:
        case_id = res.json().get("id")
        log_success(f"Created Case: {case_name} (ID: {case_id})")
    else:
        log_fail("Create Case", res.text)
        return None

    # 2. Add Message to Case
    log_info(f"Adding MSG {msg_id} to Case...")
    payload = {
        "case_id": case_id,
        "message_ids": [msg_id]
    }
    url = f"{BASE_URL}/cases/{case_id}/items?org_id={org_id}"
    res = requests.post(url, json=payload)
    log_http("POST", url, payload, res)
    if res.status_code == 200:
        log_success("Message added to case")
    else:
        log_fail("Add message to case", res.text)

    # 3. Export
    log_info("Exporting Case...")
    payload = {"format": "native", "redact": False}
    url = f"{BASE_URL}/cases/{case_id}/export?org_id={org_id}"
    res = requests.post(url, json=payload)
    log_http("POST", url, payload, res)
    if res.status_code == 200:
        log_success(f"Case Export Job Launched: {res.json().get('job_id')}")
    else:
        log_fail("Export Case", res.text)

    return case_id

def test_analytics(org_id):
    log_info("Testing Analytics...")
    url = f"{BASE_URL}/admin/analytics?org_id={org_id}"
    res = requests.get(url)
    log_http("GET", url, None, res)
    if res.status_code == 200:
        data = res.json()
        log_success(f"Analytics Data: OK (Total Messages: {data.get('total_messages')})")
    else:
        log_fail("Get Analytics", res.text)

def main():
    print(f"{Colors.HEADER}{Colors.BOLD}=== OpenArchive Verbose API Tester ==={Colors.ENDC}\n")
    
    org_id = test_organizations()
    if not org_id: return
    
    send_test_email("tester-labs.xyz")
    test_users(org_id)
    test_audit_logs(org_id)
    
    msg_info = test_messages(org_id)
    if msg_info:
        msg_id, active_org = msg_info
        test_cases(active_org, msg_id)
    
    test_legal_holds(org_id)
    test_analytics(org_id)
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== Test Run Complete ==={Colors.ENDC}")

if __name__ == "__main__":
    main()
