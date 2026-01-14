import asyncio
import os
import sys

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../core')))

import database

async def run():
    conn = await database.get_db_connection()
    try:
        print("Adding collaboration columns to case_items...")
        await conn.execute('ALTER TABLE case_items ADD COLUMN IF NOT EXISTS assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL')
        await conn.execute("ALTER TABLE case_items ADD COLUMN IF NOT EXISTS review_status TEXT DEFAULT 'PENDING'")
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run())
