import asyncio
import aiohttp
import logging
import json
import base64
import os
from buffer import get_pending_messages, mark_synced, get_pending_cas, mark_cas_synced

# Configure Logging
logger = logging.getLogger("OpenArchiveSync")

import ssl

CORE_API_URL = os.getenv("CORE_API_URL", "https://localhost:8000/api/v1/sync")
CORE_CAS_CHECK_URL = CORE_API_URL.replace("/sync", "/cas/check")
CORE_CAS_UPLOAD_URL = CORE_API_URL.replace("/sync", "/cas/upload")
API_KEY = os.getenv("CORE_API_KEY", "secret")
ORG_ID = os.getenv("AGENT_ORG_ID", "1")

async def sync_loop():
    logger.info(f"Starting Sync Loop... [Agent Org ID: {ORG_ID}]")
    
    # Configure SSL (Allow Self-Signed for Internal Agent)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        while True:
            try:
                # --- PHASE 1: CAS DEDUPLICATION ---
                pending_cas = await get_pending_cas(limit=20)
                if pending_cas:
                    hashes = [row['hash'] for row in pending_cas]
                    
                    # 1. Check Existence
                    to_upload = []
                    async with session.post(CORE_CAS_CHECK_URL, json={"hashes": hashes}, headers={"X-API-Key": API_KEY, "X-Org-ID": ORG_ID}) as resp:
                        if resp.status == 200:
                            existence_map = await resp.json()
                            to_upload = [h for h, exists in existence_map.items() if not exists]
                        else:
                             logger.error(f"CAS Check Failed: {resp.status}")
                             # If check fails, maybe upload all? or retry? Retry.
                             await asyncio.sleep(5)
                             continue

                    # 2. Upload Missing
                    if to_upload:
                        cas_batch = []
                        for row in pending_cas:
                            if row['hash'] in to_upload:
                                with open(row['storage_path'], "rb") as f:
                                    cas_batch.append({
                                        "hash": row['hash'],
                                        "blob_b64": base64.b64encode(f.read()).decode('utf-8')
                                    })
                        
                        if cas_batch:
                            async with session.post(CORE_CAS_UPLOAD_URL, json={"batch": cas_batch}, headers={"X-API-Key": API_KEY, "X-Org-ID": ORG_ID}) as resp:
                                if resp.status != 200:
                                    logger.error(f"CAS Upload Failed: {resp.status}")
                                    await asyncio.sleep(5)
                                    continue
                    
                    # 3. Mark All Synced
                    for row in pending_cas:
                        await mark_cas_synced(row['hash'])
                    logger.info(f"Synced {len(pending_cas)} CAS blobs.")

                # --- PHASE 2: MESSAGE SYNC ---
                pending = await get_pending_messages(limit=50)
                
                if not pending:
                    await asyncio.sleep(5)
                    continue
                
                msg_ids = [row['id'] for row in pending]
                logger.info(f"📤 SYNCING {len(pending)} MESSAGES | Org ID: {ORG_ID} | IDs: {msg_ids}")
                
                # 2. Prepare Batch
                batch = []
                for row in pending:
                    # Read encrypted blob
                    with open(row["storage_path"], "rb") as f:
                        blob = f.read()
                        
                    batch.append({
                        "id": row["id"],
                        "key": row["key"],
                        "metadata": json.loads(row["metadata"]),
                        "blob_b64": base64.b64encode(blob).decode('utf-8')
                    })
                
                # 3. Send to Core
                async with session.post(
                    CORE_API_URL, 
                    json={"batch": batch},
                    headers={"X-API-Key": API_KEY, "X-Org-ID": ORG_ID}
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ BATCH SYNCED SUCCESSFULLY | Sent {len(batch)} messages.")
                        # 4. Mark as Synced
                        for item in batch:
                            await mark_synced(item["id"])
                    else:
                        logger.error(f"Sync failed: {resp.status} - {await resp.text()}")
                        await asyncio.sleep(10) # Backoff
                        
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(sync_loop())
