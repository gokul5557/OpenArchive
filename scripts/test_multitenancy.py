import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"
import os
SUPER_ADMIN_KEY = os.getenv("CORE_API_KEY", "secret") 

def log(msg, type="INFO"):
    print(f"[{type}] {msg}")

def test_multitenancy():
    log("Starting Multi-Tenancy Verification...", "TEST")

    import random
    suffix = random.randint(1000, 9999)

    # 1. Create Organization A
    log("Creating Organization A...")
    try:
        res = requests.post(f"{BASE_URL}/admin/organizations", json={
            "name": f"Acme Corp {suffix}",
            "slug": f"acme-{suffix}"
        }, headers={"x-api-key": SUPER_ADMIN_KEY})
        if res.status_code == 200:
            org_a = res.json()
            org_a_id = org_a['id']
            log(f"Created Org A: {org_a['name']} (ID: {org_a_id})", "SUCCESS")
        else:
            log(f"Failed to create Org A: {res.text}", "ERROR")
            return
    except Exception as e:
        log(f"Connection Failed: {e}", "CRITICAL")
        return

    # 2. Create Organization B
    log("Creating Organization B...")
    res = requests.post(f"{BASE_URL}/admin/organizations", json={
        "name": f"Beta Inc {suffix}",
        "slug": f"beta-{suffix}"
    }, headers={"x-api-key": SUPER_ADMIN_KEY})
    org_b = res.json()
    org_b_id = org_b['id']
    log(f"Created Org B: {org_b['name']} (ID: {org_b_id})", "SUCCESS")

    # 3. Create Case in Org A
    log("Creating Case in Org A...")
    res = requests.post(f"{BASE_URL}/cases?org_id={org_a_id}", json={
        "name": "Acme Investigation",
        "description": "Internal Audit"
    })
    if res.status_code == 200:
        case_a = res.json()
        log(f"Created Case in Org A: {case_a['id']}", "SUCCESS")
    else:
        log(f"Failed to create Case in Org A: {res.text}", "ERROR")

    # 4. Verify Org B CANNOT see Org A's case
    log("Verifying Isolation (Org B listing cases)...")
    res = requests.get(f"{BASE_URL}/cases?org_id={org_b_id}")
    cases_b = res.json()
    
    found = any(c['id'] == case_a['id'] for c in cases_b)
    if not found:
        log("Isolation Verified: Org B cannot see Org A's case.", "SUCCESS")
    else:
        log("Security Breach: Org B CAN see Org A's case!", "FAIL")

    # 5. Create Legal Hold in Org B
    log("Creating Legal Hold in Org B...")
    res = requests.post(f"{BASE_URL}/admin/holds?org_id={org_b_id}", json={
        "name": "Beta Litigation",
        "reason": "Lawsuit",
        "filter_criteria": {}
    })
    hold_b = res.json()
    log(f"Created Hold in Org B: {hold_b['id']}", "SUCCESS")

    # 6. Verify Org A CANNOT see Org B's hold
    log("Verifying Isolation (Org A listing holds)...")
    res = requests.get(f"{BASE_URL}/admin/holds?org_id={org_a_id}")
    holds_a = res.json()
    
    found_hold = any(h['id'] == hold_b['id'] for h in holds_a)
    if not found_hold:
        log("Isolation Verified: Org A cannot see Org B's hold.", "SUCCESS")
    else:
        log("Security Breach: Org A CAN see Org B's hold!", "FAIL")

    # 7. Verify Super Admin can list all Orgs
    log("Verifying Super Admin Org List...")
    res = requests.get(f"{BASE_URL}/admin/organizations", headers={"x-api-key": SUPER_ADMIN_KEY})
    orgs = res.json()
    if len(orgs) >= 2:
         log(f"Super Admin sees {len(orgs)} organizations.", "SUCCESS")
    else:
         log("Super Admin failed to list organizations.", "FAIL")

if __name__ == "__main__":
    test_multitenancy()
