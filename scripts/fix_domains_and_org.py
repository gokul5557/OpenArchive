import asyncio
import os
from meilisearch import Client

MEILI_HOST = os.getenv("MEILI_HOST", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

async def fix_data():
    client = Client(MEILI_HOST, MEILI_KEY)
    index = client.index('emails')
    
    # 1. Fetch ALL docs (limit high)
    # We look for ORG 6 (where I moved them) AND ORG 13 (just in case)
    # Actually, let's just fetch everything for now since it's a dev env.
    print("Fetching documents...")
    # Get all docs matching sagasoft
    hits = index.search('sagasoft', {'limit': 10000})['hits']
    print(f"Scanned {len(hits)} documents matching 'sagasoft'.")
    
    updates = []
    count = 0
    for h in hits:
        changed = False
        
        # Helper to get flat org_id
        oid = h.get('org_id')
        
        # Check if it's 6 or [6]
        is_org_6 = False
        if isinstance(oid, int) and oid == 6: is_org_6 = True
        elif isinstance(oid, list) and 6 in oid: is_org_6 = True
        
        if is_org_6:
             # Set to 13 (Integer or List? Backend uses List now)
             # Let's verify what 'main.py' uses. It set it equal to `resolved_org_ids` which is a list.
             # But older docs might be int? Meilisearch is schema-less.
             # We set it to 13 (int) to be compatible with my previous assumptions OR [13].
             # Let's set it to 13 (int) because `search_messages` does `org_id = {org_id}`.
             # Meilisearch handles `filter="org_id = 13"` correctly for `13` or `[13]`.
             # But let's stick to int if that's what we want, or list if required.
             # The sample doc I saw earlier from `curl` had `org_id: 6` (int). 
             # So I will set it to 13 (int).
             h['org_id'] = 13
             changed = True
             
        # FIX 2: Clean Domains
        if 'domains' in h and isinstance(h['domains'], list):
            clean_domains = []
            domains_changed = False
            for d in h['domains']:
                clean = d.rstrip('>')
                if clean != d: domains_changed = True
                clean_domains.append(clean)
            
            if domains_changed:
                h['domains'] = clean_domains
                changed = True
        
        if changed:
            updates.append(h)
            count += 1
            if count <= 1: print(f"Sample Update: {h}")
            
    if updates:
        print(f"Updating {count} documents...")
        task = index.update_documents(updates)
        print(f"Task UID: {task.task_uid}")
    else:
        print("No updates needed.")

if __name__ == "__main__":
    asyncio.run(fix_data())
