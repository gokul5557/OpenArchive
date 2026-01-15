import asyncpg
import os
import asyncio
import json
try:
    import security
except ImportError:
    from core import security

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Global Pool
pool = None

async def connect():
    global pool
    if not pool:
        print("Initializing Database Connection Pool...")
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
        print("Database Pool Initialized.")

async def disconnect():
    global pool
    if pool:
        await pool.close()
        print("Database Pool Closed.")

async def get_db_connection():
    global pool
    if not pool:
        await connect()
    return await pool.acquire()

async def init_db():
    # Use direct connection for initialization if pool not ready (or just use pool)
    conn = await get_db_connection()
    try:
        # 1. Organizations Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Schema Migration: Add domains if missing
        try:
            await conn.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS domains TEXT[] DEFAULT '{}'")
        except Exception as e:
            print(f"Migration error (domains): {e}")

        # Schema Migration: Add password_hash if missing
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
        except Exception as e:
            print(f"Migration error (password_hash): {e}")

        # Schema Migration: Add totp_secret if missing
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT")
        except Exception as e:
            print(f"Migration error (totp_secret): {e}")

        # Seed Default Org
        exists_org = await conn.fetchval("SELECT 1 FROM organizations WHERE slug = 'default'")
        if not exists_org:
            await conn.execute("INSERT INTO organizations (name, slug) VALUES ('Default Organization', 'default')")
            print("Initialized Default Organization.")

        # Seed Sagasoft Org (for local dev/testing)
        exists_saga = await conn.fetchval("SELECT 1 FROM organizations WHERE slug = 'sagasoft'")
        if not exists_saga:
            await conn.execute("""
                INSERT INTO organizations (name, slug, domains) 
                VALUES ('Sagasoft', 'sagasoft', '{"sagasoft.xyz", "sagasoft.io"}')
            """)
            print("Initialized Sagasoft Organization.")
        else:
            # Update domains if already exists
            await conn.execute("""
                UPDATE organizations 
                SET domains = '{"sagasoft.xyz", "sagasoft.io"}' 
                WHERE slug = 'sagasoft'
            """)

        # 2. Users Table (Updated)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL, -- 'super_admin', 'client_admin', 'auditor'
                org_id INTEGER REFERENCES organizations(id),
                domains JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # User Seed (Super Admin) promotion or creation
        default_org_id = await conn.fetchval("SELECT id FROM organizations WHERE slug = 'default'")
        exists_admin = await conn.fetchval("SELECT 1 FROM users WHERE username = 'admin'")
        if not exists_admin:
            p_hash = security.get_password_hash("admin")
            await conn.execute("""
                INSERT INTO users (username, role, org_id, domains, password_hash) 
                VALUES ('admin', 'super_admin', $1, '[]', $2)
            """, default_org_id, p_hash)
            print("Initialized Super Admin user.")
        else:
            # Update role and ensure password hash exists if missing (reset to admin)
            p_hash = security.get_password_hash("admin")
            # Only reset if NULL? Or force reset for dev? 
            # Force reset to ensure we can login after backdoor removal
            await conn.execute("UPDATE users SET role = 'super_admin', org_id = $1, password_hash = $2 WHERE username = 'admin'", default_org_id, p_hash)

        # 3. Audit Log Table (Updated)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                org_id INTEGER REFERENCES organizations(id),
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                details JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                previous_hash TEXT,
                current_hash TEXT
            );
        """)

        # RLS Security Policy
        try:
            # Enable RLS
            await conn.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
            
            # Create Policy (Idempotent)
            await conn.execute("""
                DO $$ BEGIN
                    CREATE POLICY tenant_isolation ON audit_logs
                    USING (
                        current_setting('app.current_role', true) = 'super_admin' 
                        OR 
                        org_id = current_setting('app.current_org_id', true)::int
                    );
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END $$;
            """)
            print("RLS Policy Enabled on audit_logs.")
        except Exception as e:
            print(f"RLS Setup Error: {e}")

        # 4. Legal Hold Table (Updated)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS legal_holds (
                id SERIAL PRIMARY KEY,
                org_id INTEGER REFERENCES organizations(id),
                name TEXT NOT NULL,
                reason TEXT,
                filter_criteria JSONB NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT TRUE,
                public_id TEXT UNIQUE
            );
        """)

        # Legal Hold Items (Remains same, linked to hold_id)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS legal_hold_items (
                id SERIAL PRIMARY KEY,
                hold_id INTEGER REFERENCES legal_holds(id) ON DELETE CASCADE,
                message_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(hold_id, message_id)
            );
        """)
        
        # 5. Retention Policies Table (Updated)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS retention_policies (
                id SERIAL PRIMARY KEY,
                org_id INTEGER REFERENCES organizations(id),
                name TEXT NOT NULL,
                domains JSONB DEFAULT '[]'::jsonb,
                retention_days INTEGER NOT NULL,
                action TEXT DEFAULT 'PERMANENT_DELETE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT TRUE
            );
        """)

        # 6. eDiscovery Cases Table (Updated)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id SERIAL PRIMARY KEY,
                org_id INTEGER REFERENCES organizations(id),
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'OPEN',
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Case Items (Remains same, linked to case_id)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS case_items (
                id SERIAL PRIMARY KEY,
                case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
                message_id TEXT NOT NULL,
                tags JSONB DEFAULT '[]'::jsonb, 
                added_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                review_status TEXT DEFAULT 'PENDING',
                UNIQUE(case_id, message_id)
            );
        """)

        # 7. Sidecar Agents Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sidecar_agents (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                hostname TEXT,
                org_id INTEGER REFERENCES organizations(id),
                status TEXT DEFAULT 'OFFLINE',
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print("Database Schema Finalized for Multi-Tenancy.")
        
    except Exception as e:
        print(f"DB Initialization Error: {e}")
    finally:
        # Release connection back to pool
        await conn.close()


create_tables = init_db

if __name__ == "__main__":
    asyncio.run(init_db())
