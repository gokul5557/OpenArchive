import aiosqlite
import json
import os
import uuid
import datetime

DB_PATH = os.getenv("SIDECAR_DB_PATH", "buffer.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                metadata TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cas_blobs (
                hash TEXT PRIMARY KEY,
                storage_path TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def save_message(message_id: str, key: bytes, metadata: dict, encrypted_blob: bytes):
    """Saves encrypted blob to disk and metadata to DB."""
    
    # Ensure storage directory exists
    storage_dir = "data/buffer"
    os.makedirs(storage_dir, exist_ok=True)
    
    storage_path = os.path.join(storage_dir, f"{message_id}.enc")
    
    # write blob to disk
    with open(storage_path, "wb") as f:
        f.write(encrypted_blob)
        
    # save to DB
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (id, key, metadata, storage_path) VALUES (?, ?, ?, ?)",
            (message_id, key.decode('utf-8'), json.dumps(metadata), storage_path)
        )
        await db.commit()

async def get_pending_messages(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM messages WHERE status = 'PENDING' LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

async def mark_synced(message_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE messages SET status = 'SYNCED' WHERE id = ?", (message_id,))
        await db.commit()
        
        # Optional: Delete local blob after sync if configured to do so
    # For now, we keep it or rely on a separate cleanup policy

async def save_cas_blob(blob_hash: str, blob_data: bytes):
    """Saves CAS blob if not exists locally."""
    storage_dir = "data/cas"
    os.makedirs(storage_dir, exist_ok=True)
    storage_path = os.path.join(storage_dir, f"{blob_hash}.bin")
    
    # Write to disk
    if not os.path.exists(storage_path):
        with open(storage_path, "wb") as f:
            f.write(blob_data)

    async with aiosqlite.connect(DB_PATH) as db:
        # Check if exists
        async with db.execute("SELECT 1 FROM cas_blobs WHERE hash = ?", (blob_hash,)) as cursor:
            if await cursor.fetchone():
                return 

        await db.execute(
            "INSERT INTO cas_blobs (hash, storage_path) VALUES (?, ?)",
            (blob_hash, storage_path)
        )
        await db.commit()

async def get_pending_cas(limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cas_blobs WHERE status = 'PENDING' LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

async def mark_cas_synced(blob_hash: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE cas_blobs SET status = 'SYNCED' WHERE hash = ?", (blob_hash,))
        await db.commit()
