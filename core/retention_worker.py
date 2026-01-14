import asyncio
import logging
import time
from datetime import datetime, timedelta
import database
import storage
import search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RetentionWorker")

async def purge_expired_messages():
    """Identifies and deletes messages past their retention period (if not held)."""
    conn = await database.get_db_connection()
    try:
        # 1. Get Retention Policies
        policies = await conn.fetch("SELECT domains, retention_days FROM retention_policies")
        if not policies:
            logger.info("No retention policies defined. Skipping purge.")
            return
        
        # ... logic to handle each domain in the policy list ...
        # (Actually I need to loop through the policies and then through domains)

        # 2. Get all Held Message IDs (Total Protection)
        held_rows = await conn.fetch("SELECT message_id FROM legal_hold_items")
        held_ids = {r['message_id'] for r in held_rows}
        
        # 3. Get Account Holds (Domains/Emails)
        account_holds = await conn.fetch("SELECT filter_criteria FROM legal_holds WHERE active = TRUE")
        held_emails = set()
        for h in account_holds:
            import json
            crit = json.loads(h['filter_criteria'])
            if crit.get('from'): held_emails.add(crit['from'])
            if crit.get('to'): held_emails.add(crit['to'])

        for policy in policies:
            import json
            p_domains = json.loads(policy['domains'])
            days = policy['retention_days']
            cutoff_ts = int((datetime.utcnow() - timedelta(days=days)).timestamp())
            
            for domain in p_domains:
                logger.info(f"Purging messages for {domain} older than {days} days (cutoff TS: {cutoff_ts})")
                
                # 4. Search Meili for candidates
                filter_query = f"domains = '{domain}' AND date_timestamp < {cutoff_ts}"
                results = search.search_documents(query="", filter_query=filter_query, limit=1000)
                
                candidates = results.get('hits', [])
                purged_count = 0
                
                for msg in candidates:
                    mid = msg['id']
                    
                    # PROTECTION CHECK
                    if mid in held_ids:
                        logger.debug(f"Skipping {mid}: Explicitly Held.")
                        continue
                    
                    if msg.get('from') in held_emails or msg.get('to') in held_emails:
                        logger.debug(f"Skipping {mid}: Associated with Held Account.")
                        continue
                    
                    # PERMANENT DELETE
                    try:
                        # Remove from Search
                        search.client.index('emails').delete_document(mid)
                        # Remove from Storage
                        storage.delete_blob(f"{mid}.enc")
                        
                        purged_count += 1
                    except Exception as e:
                        logger.error(f"Failed to purge {mid}: {e}")

                if purged_count > 0:
                    logger.info(f"Successfully purged {purged_count} messages for {domain}.")

    except Exception as e:
        logger.error(f"Purge Error: {e}")
    finally:
        await conn.close()

async def start_worker():
    logger.info("Retention Worker Started. Running every 24 hours.")
    while True:
        await purge_expired_messages()
        # Sleep 24 hours
        await asyncio.sleep(86400)

if __name__ == "__main__":
    asyncio.run(start_worker())
