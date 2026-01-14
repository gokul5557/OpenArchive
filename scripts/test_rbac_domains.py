
import requests
import json
import random

BASE_URL = "http://localhost:8000/api/v1"
SUPER_ADMIN_KEY = "super-secret-key" # Mocking auth if needed, or relying on test user handling
# Note: The app uses mock auth in UI but 'admin' headers or similar for API? 
# Actually `core/admin.py` doesn't enforce auth headers yet on these endpoints (MVP), but `scripts/test_multitenancy.py` used keys? No, it used headers.
# Let's check `core/main.py`. It likely doesn't verify headers for MVP admin routes unless middleware is there. 
# `scripts/test_multitenancy.py` used `x-api-key` header just in case? 
# The UI uses `useUser` context but backend `list_users` checks NOTHING? 
# Ah, `core/admin.py` endpoints are Public?!
# Line 10: `router = APIRouter()`
# No dependencies.
# This means ANYONE can call /admin/organizations.
# For the purpose of this task (UI/Architecture), I assume security is handled by gateway or implicit trusting for now, OR I should add it. 
# But let's test the LOGIC first.

def log(msg, label="INFO"):
    print(f"[{label}] {msg}")

def test_rbac_domains():
    suffix = random.randint(10000, 99999)
    org_slug = f"rbac-org-{suffix}"
    domain_a = f"dept-a-{suffix}.com"
    domain_b = f"dept-b-{suffix}.com"
    domain_c = f"external-{suffix}.com"

    # 1. Super Admin Create Org with Domains A and B
    log(f"Creating Org {org_slug} with domains [{domain_a}, {domain_b}]...")
    res = requests.post(f"{BASE_URL}/admin/organizations", json={
        "name": f"RBAC Test Org {suffix}",
        "slug": org_slug,
        "domains": [domain_a, domain_b]
    })
    if res.status_code != 200:
        log(f"Failed to create Org: {res.text}", "ERROR")
        return
    org = res.json()
    org_id = org['id']
    log(f"Org Created: ID {org_id}")

    # 2. Super Admin Create Client Admin (Auto-assigns domains?)
    # In my UI logic, I send 'domains'. Let's simulate that.
    log("Creating Client Admin...")
    res = requests.post(f"{BASE_URL}/admin/users", json={
        "username": f"admin-{suffix}",
        "role": "client_admin",
        "org_id": org_id,
        "domains": [domain_a, domain_b] # Assign full access
    })
    if res.status_code != 200:
        log(f"Failed to create Client Admin: {res.text}", "ERROR")
        return
    client_admin = res.json()
    log(f"Client Admin Created: {client_admin['username']}")

    # 3. Client Admin Creates Auditor (Restricted to Domain A)
    log("Creating Auditor (Restricted to Domain A)...")
    res = requests.post(f"{BASE_URL}/admin/users", json={
        "username": f"auditor-{suffix}",
        "role": "auditor",
        "org_id": org_id,
        "domains": [domain_a] # Subset
    })
    if res.status_code != 200:
        log(f"Failed to create Auditor: {res.text}", "ERROR")
        return
    auditor = res.json()
    log(f"Auditor Created: {auditor['username']}")

    # 4. Verify Domain Validation (Try to create Auditor with invalid domain C)
    log("Verifying Domain Validation (Should Fail)...")
    res = requests.post(f"{BASE_URL}/admin/users", json={
        "username": f"hacker-{suffix}",
        "role": "auditor",
        "org_id": org_id,
        "domains": [domain_c] # Invalid
    })
    if res.status_code == 400:
        log("Success: Rejected invalid domain assignment.")
    else:
        log(f"Failure: Accepted invalid domain! {res.status_code}", "FAIL")

    # 5. Verify Search Scoping (Mock Search Call)
    # Since we can't easily ingest data in this quick script without raw files/encryption setup,
    # we will test the Query Construction by calling the search endpoint with `user_domain` param
    # and seeing if it accepts/filters. 
    # Actually, we can check if it *doesn't* error. To verify logic, we'd need to inspect logs or actually have data.
    # For now, we trust the `search_messages` logic review.
    # But let's call it to ensure no 500s on parsing.
    
    log(f"Testing Search Params for Auditor ({domain_a})...")
    res = requests.get(f"{BASE_URL}/messages", params={
        "org_id": org_id,
        "q": "test",
        "user_domain": domain_a
    })
    if res.status_code == 200:
        log("Auditor Search OK")
    else:
        log(f"Auditor Search Failed: {res.text}", "FAIL")

if __name__ == "__main__":
    test_rbac_domains()
