import asyncio
import logging
import json
import database
import integrity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntegrityWorker")

async def verify_chains():
    """Verifies the hash chain integrity for all organizations."""
    try:
        # We need a SUPER ADMIN connection to bypass RLS for this worker!
        # Assuming the worker runs with Super Admin privileges or bypassing RLS.
        # How to bypass RLS in worker?
        # Option 1: Set 'app.current_role' = 'super_admin' on connection.
        conn = await database.get_db_connection()
        try:
            # Set Super Admin Context
            await conn.execute("SELECT set_config('app.current_role', 'super_admin', false)")
            
            # Get All Orgs
            orgs = await conn.fetch("SELECT id, name FROM organizations")
            
            for org in orgs:
                oid = org['id']
                logger.debug(f"Verifying Audit Chain for Org {oid} ({org['name']})...")
                
                # Fetch Logs sequentially
                # Note: For huge logs, this should be paginated or streamed. 
                # For MVP/PoC, fetching all.
                rows = await conn.fetch("SELECT id, username, action, details, previous_hash, current_hash FROM audit_logs WHERE org_id = $1 ORDER BY id ASC", oid)
                
                if not rows:
                    continue
                    
                last_hash = "ROOT_HASH"
                for r in rows:
                    failed = False
                    reason = ""
                    
                    # 1. Check Previous Link
                    if r['previous_hash'] != last_hash:
                        failed = True
                        reason = f"Link Mismatch at ID {r['id']}. Expected prev={last_hash}, Got={r['previous_hash']}"
                    
                    # 2. Verify Computation
                    else:
                        # Re-compute
                        # Need to ensure details formatting matches exactly what was inserted.
                        # admin.py uses json.dumps(details, sort_keys=True)
                        details_val = r['details']
                        if isinstance(details_val, str):
                            details_dict = json.loads(details_val)
                        else:
                            details_dict = details_val if details_val else {}
                            
                        details_str = json.dumps(details_dict, sort_keys=True)
                        
                        payload = f"{r['previous_hash']}{r['username']}{r['action']}{details_str}{oid}"
                        expected_hash = integrity.calculate_hash(payload.encode())
                        
                        if r['current_hash'] != expected_hash:
                            failed = True
                            reason = f"Hash Mismatch at ID {r['id']}. Re-computed={expected_hash}, Stored={r['current_hash']}"
                    
                    if failed:
                        logger.error(f"[SECURITY ALERT] TAMPERING DETECTED in Org {oid}: {reason}")
                        # In real world: Send Email / Slack Alert / SNMP Trap
                        break # Stop checking this chain
                    
                    last_hash = r['current_hash']
                    
                else:
                    logger.debug(f"Org {oid} Audit Chain Integrated Verified ({len(rows)} entries).")

        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Integrity Worker Error: {e}")

async def start_worker():
    logger.info("Integrity Worker Started. Running every 10 minutes.")
    while True:
        await verify_chains()
        await asyncio.sleep(600) # 10 minutes

if __name__ == "__main__":
    asyncio.run(start_worker())
