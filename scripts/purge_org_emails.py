import asyncio
import os
import asyncpg
from meilisearch import Client
from dotenv import load_dotenv
import boto3

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MEILI_HOST = os.getenv("MEILI_HOST", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "password")
BUCKET_NAME = "archive-blobs"

ORG_ID = 13  # sagasoft.xyz

async def purge_emails():
    print(f"⚠️  STARTING PURGE FOR ORG ID: {ORG_ID} ⚠️")
    
    # Setup Clients
    meili = Client(MEILI_HOST, MEILI_KEY)
    index = meili.index('emails')
    
    s3 = boto3.client(
        's3', 
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY
    )

    # 1. Fetch IDs from Meilisearch
    print("Fetching IDs from Meilisearch...")
    all_ids = []
    offset = 0
    limit = 1000
    while True:
        res = index.search('', {'filter': f'org_id = {ORG_ID}', 'limit': limit, 'offset': offset})
        hits = res.get('hits', [])
        if not hits:
            break
        all_ids.extend([h['id'] for h in hits])
        offset += limit
        print(f"  Found {len(all_ids)} messages so far...")

    if not all_ids:
        print("No messages found for this Org.")
        return

    print(f"Found total {len(all_ids)} messages to purge.")

    # 2. Delete from MinIO
    print("Deleting Blobs from MinIO...")
    deleted_blobs = 0
    for mid in all_ids:
        try:
            object_name = f"{mid}.enc"
            s3.delete_object(Bucket=BUCKET_NAME, Key=object_name)
            deleted_blobs += 1
        except Exception as e:
            print(f"  Failed to delete blob {object_name}: {e}")
    print(f"✅ Deleted {deleted_blobs} blobs.")
    
    # 3. Delete from Meilisearch
    print("Deleting from Meilisearch...")
    task = index.delete_documents(all_ids)
    meili.wait_for_task(task.task_uid)
    print("✅ Deleted documents from Meilisearch.")

    # 4. Clean Postgres References
    print("Cleaning Postgres References...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Legal Hold Items
        res = await conn.execute("DELETE FROM legal_hold_items WHERE message_id = ANY($1)", all_ids)
        print(f"  {res}")
        
        # Case Items
        res = await conn.execute("DELETE FROM case_items WHERE message_id = ANY($1)", all_ids)
        print(f"  {res}")

    finally:
        await conn.close()

    print("🎉 PURGE COMPLETED.")

if __name__ == "__main__":
    asyncio.run(purge_emails())
