import asyncio
import asyncpg
import json

import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/openarchive")

async def main():
    print("Connecting to DB...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check Audit Logs
        # We expect ACTION = 'SMTP_INGEST' for Org 8 (domain1.com)
        row = await conn.fetchrow("""
            SELECT * FROM audit_logs 
            WHERE org_id = 8 AND action = 'SMTP_INGEST' 
            ORDER BY id DESC LIMIT 1
        """)
        
        if row:
            print(f"SUCCESS: Found SMTP Audit Log.")
            print(f"Details: {row['details']}")
            print(f"Current Hash: {row['current_hash']}")
        else:
            print("FAILURE: No SMTP Audit Log found.")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
