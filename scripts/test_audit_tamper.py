import asyncio
import aiohttp
import sys
import os
import json
import asyncpg

# Direct access to tamper
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/openarchive")
BASE_URL = "http://localhost:8000/api/v1"

async def main():
    print("--- Audit Tamper Test ---")
    
    # 1. Create Valid Log
    print("Creating Valid Log...")
    async with aiohttp.ClientSession() as session:
        log_data = {
            "username": "test_user",
            "action": "TEST_ACTION",
            "details": {"test": "valid"}
        }
        # Org 8
        async with session.post(f"{BASE_URL}/admin/audit-logs?org_id=8", json=log_data) as resp:
            if resp.status != 200:
                print(f"Failed to create log: {await resp.text()}")
                return
            res_json = await resp.json()
            print(f"Log Created. Hash: {res_json.get('hash')}")
            
    # 2. Verify Chain (Should be Valid)
    print("Verifying Chain (Pre-Tamper)...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/admin/audit-logs/verify?org_id=8") as resp:
            print(f"Verify Status: {resp.status}")
            txt = await resp.text()
            print(txt)
            if '"valid":true' not in txt:
                print("FAILURE: Chain invalid initially.")
                return

    # 3. Tamper with DB (Update details of the last log)
    print("Tampering with DB...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # We need to bypass RLS to update? 
        # Or use Super Admin / correct context.
        # Direct SQL via asyncpg usually connects as 'admin' (superuser in docker?).
        # If 'admin' is superuser, RLS is bypassed (BYPASSRLS attribute) or policy allows super_admin role.
        # Docker postgres 'admin' usually has all privileges.
        # BUT our policy checks `app.current_role`.
        # If I don't set it, default deny?
        # Unless user is superuser (Postgres superuser ignores RLS).
        
        # Modify the last inserted log
        await conn.execute("""
            UPDATE audit_logs 
            SET details = '{"test": "tampered"}'::jsonb 
            WHERE action = 'TEST_ACTION'
        """)
        print("Tampered with Log.")
    except Exception as e:
        print(f"Tamper Error: {e}")
    finally:
        await conn.close()

    # 4. Verify Chain (Should be Invalid)
    print("Verifying Chain (Post-Tamper)...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/admin/audit-logs/verify?org_id=8") as resp:
            print(f"Verify Status: {resp.status}")
            txt = await resp.text()
            print(txt)
            if '"valid":false' in txt:
                print("SUCCESS: Tampering Detected!")
            else:
                print("FAILURE: Tampering NOT Detected.")

if __name__ == "__main__":
    asyncio.run(main())
