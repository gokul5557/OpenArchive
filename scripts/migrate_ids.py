import asyncio
import asyncpg
import os
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/openarchive")

async def migrate_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Checking for public_id column...")
        # Check if column exists
        col_exists = await conn.fetchval("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='legal_holds' AND column_name='public_id'
        """)
        
        if not col_exists:
            print("Adding public_id column...")
            await conn.execute("ALTER TABLE legal_holds ADD COLUMN public_id TEXT")
            await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_legal_holds_public_id ON legal_holds(public_id)")
            
            # Backfill
            print("Backfilling UUIDs...")
            rows = await conn.fetch("SELECT id FROM legal_holds WHERE public_id IS NULL")
            for row in rows:
                uid = str(uuid.uuid4())
                await conn.execute("UPDATE legal_holds SET public_id = $1 WHERE id = $2", uid, row['id'])
            
            print("Migration Complete.")
        else:
            print("Column public_id already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_db())
