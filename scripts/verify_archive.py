import asyncio
import os
import sys
import json

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../core')))

import database
import storage
import search
import integrity

async def verify_messages():
    print("--- Verifying Message Integrity ---")
    # Fetch all docs from Meili
    index = search.client.index('emails')
    res = index.get_documents({'limit': 1000}) # Adjust limit if needed
    docs = res.results if hasattr(res, 'results') else res
    
    valid_count = 0
    fail_count = 0
    missing_sig = 0
    
    for doc in docs:
        mid = getattr(doc, 'id', None)
        sig = getattr(doc, 'signature', None)
        
        if not sig:
            missing_sig += 1
            continue
            
        blob = storage.get_blob(f"{mid}.enc")
        if not blob:
            print(f"FAILED: {mid} - Blob missing")
            fail_count += 1
            continue
            
        if integrity.verify_integrity(blob, sig):
            valid_count += 1
        else:
            print(f"FAILED: {mid} - SIGNATURE MISMATCH (TAMPERED)")
            fail_count += 1
            
    print(f"Messages: {valid_count} Valid, {fail_count} Failed, {missing_sig} No Signature (Legacy)")
    return fail_count == 0

async def verify_audit_chain():
    print("\n--- Verifying Audit Log Chain ---")
    conn = await database.get_db_connection()
    try:
        rows = await conn.fetch("SELECT id, username, action, details, previous_hash, current_hash FROM audit_logs ORDER BY id ASC")
        
        last_hash = "ROOT_HASH"
        for r in rows:
            if not r['current_hash'] or not r['previous_hash']:
                print(f"Skipping legacy audit log ID {r['id']}")
                continue

            # Check Link
            if r['previous_hash'] != last_hash:
                print(f"FAILED: Chain broken at ID {r['id']}")
                return False
                
            # Verify Content
            details_str = json.dumps(json.loads(r['details']) if r['details'] else {}, sort_keys=True)
            payload = f"{r['previous_hash']}{r['username']}{r['action']}{details_str}"
            expected = integrity.calculate_hash(payload.encode())
            
            if r['current_hash'] != expected:
                print(f"FAILED: Integrity failure at ID {r['id']}")
                return False
                
            last_hash = r['current_hash']
            
        print(f"Audit Chain: VERIFIED ({len(rows)} entries)")
        return True
    finally:
        await conn.close()

async def main():
    m_ok = await verify_messages()
    a_ok = await verify_audit_chain()
    
    if m_ok and a_ok:
        print("\nSUCCESS: System integrity verified.")
    else:
        print("\nFAILURE: System integrity compromised.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
