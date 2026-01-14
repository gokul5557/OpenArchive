import asyncio
import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/openarchive")

async def check_orgs():
    conn = await asyncpg.connect(DATABASE_URL)
    orgs = await conn.fetch("SELECT * FROM organizations")
    print("Organizations:")
    for o in orgs:
        print(dict(o))
    
    users = await conn.fetch("SELECT * FROM users")
    print("\nUsers:")
    for u in users:
        print(dict(u))
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_orgs())
