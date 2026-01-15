import asyncio
import os
from core.database import get_db_connection

async def create_org(name, org_id):
    conn = await get_db_connection()
    try:
        # Check if exists
        exists = await conn.fetchval("SELECT id FROM organizations WHERE id = $1", org_id)
        if exists:
            print(f"Organization {org_id} already exists.")
            return

        # Insert
        await conn.execute("""
            INSERT INTO organizations (id, name, slug, domains)
            VALUES ($1, $2, $3, $4)
        """, org_id, name, name.lower().replace(' ', '-'), [])
        print(f"Organization '{name}' (ID: {org_id}) created.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    # Ensure environment variables for DB are set
    # Using defaults matching server.log context or typical local dev
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5435/archive"
    
    asyncio.run(create_org("Simulation Org", 13))
