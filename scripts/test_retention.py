import asyncio
import aiohttp
import sys
import os
import json

# Add core to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../core'))
import search

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_KEY = "secret" # Not used for retention run if no auth, but good to have.
# In admin.py, dependencies might require auth? 
# admin.py router uses dependencies? 
# The endpoints `list_retention_policies` etc don't seem to have `Depends(get_current_user)` on the router level?
# Let's check admin.py router definition.
# If not protected, I can call freely.

async def main():
    print("--- Starting Retention Test ---")
    
    # 1. Get Initial Stats for domain1.com
    # domain1.com is in Org 8.
    # I can use Meili directly or API.
    query = "domains = 'domain1.com'"
    s1 = search.get_stats(filter_query=query)
    count_initial = s1['total_emails']
    print(f"Initial Emails for domain1.com: {count_initial}")
    
    if count_initial == 0:
        print("Error: No emails to test with. Run seed_data.py first.")
        return

    # 2. Create Retention Policy (1 Day)
    print("Creating Retention Policy (1 Day) for domain1.com...")
    # Org 8 is where domain1.com resides (from seed log).
    # But I need to know the Org ID. I'll search for it or assume 8.
    # Actually I can create policy with org_id=8.
    
    async with aiohttp.ClientSession() as session:
        # Create Policy
        policy_data = {
            "name": "Test Retention 1 Day",
            "domains": ["domain1.com"],
            "retention_days": 1,
            "action": "PERMANENT_DELETE"
        }
        async with session.post(f"{BASE_URL}/admin/retention?org_id=8", json=policy_data) as resp:
            if resp.status != 200:
                print(f"Failed to create policy: {await resp.text()}")
                return
            res_json = await resp.json()
            policy_id = res_json['id']
            print(f"Policy Created (ID: {policy_id})")

        # 3. Trigger Retention Run
        print("Triggering Manual Retention Run...")
        async with session.post(f"{BASE_URL}/admin/retention/run") as resp:
            print(f"Trigger Status: {resp.status}")
            print(await resp.text())
            
        # Wait a bit for async deletion (it interacts with Meili/Storage serial/parallel)?
        # The worker awaits deletion. So when API returns, it MIGHT be done? 
        # API calls `await retention_worker.purge_expired_messages()`. 
        # Yes, it is awaited. So it is synchronous for the API caller (though it loops).
        
    # 4. Check Stats Again
    print("Checking Stats after Purge...")
    # Refresh index stats might take a moment?
    # Ensure index.
    
    s2 = search.get_stats(filter_query=query)
    count_after = s2['total_emails']
    print(f"Emails for domain1.com AFTER purge: {count_after}")
    
    if count_after < count_initial:
        print(f"SUCCESS: Deleted {count_initial - count_after} emails.")
    else:
        print("FAILURE: No emails deleted. Check if emails are actually older than 1 day.")

    # 5. Cleanup Policy
    print("Cleaning up Policy...")
    async with aiohttp.ClientSession() as session:
        await session.delete(f"{BASE_URL}/admin/retention/{policy_id}?org_id=8")

if __name__ == "__main__":
    asyncio.run(main())
