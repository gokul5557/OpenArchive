import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/openarchive"

async def migrate():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS domains TEXT[] DEFAULT '{}'")
        print("Migration successful: Added domains to organizations.")
        await conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
