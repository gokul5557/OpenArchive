import asyncio
import sys
import os
import asyncpg

# Direct asyncpg test
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/openarchive")

async def main():
    print("Connecting...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Setting Context...")
        await conn.execute("SELECT set_config('app.current_org_id', '8', false)")
        await conn.execute("SELECT set_config('app.current_role', 'client_admin', false)")
        print("Context Set.")
        
        print("Querying Audit Logs...")
        rows = await conn.fetch("SELECT * FROM audit_logs LIMIT 1")
        print(f"Rows: {len(rows)}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
