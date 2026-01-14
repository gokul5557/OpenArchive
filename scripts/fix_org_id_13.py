import asyncio
import asyncpg
import os
from meilisearch import Client

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/openarchive")
MEILI_HOST = os.getenv("MEILI_HOST", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

async def fix_org_id():
    print("Connecting to DB...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    # 1. Update Messages (Actually we can't update messages table as it doesn't exist, skip this)
    # But Meili needs update.
    
    # Update Meilisearch
    print("Triggering Meilisearch Update...")
    client = Client(MEILI_HOST, MEILI_KEY)
    index = client.index('emails')
    
    hits = index.search('', {'filter': 'org_id = 13', 'limit': 10000})['hits']
    print(f"Found {len(hits)} documents in Meili with Org 13.")
    
    if hits:
        updates = []
        for h in hits:
            h['org_id'] = 6
            updates.append(h)
        
        task = index.update_documents(updates)
        print(f"Update task submitted: {task.task_uid}")

if __name__ == "__main__":
    asyncio.run(fix_org_id())
