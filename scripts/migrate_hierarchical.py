import asyncio
import asyncpg
import os
import json

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/openarchive")

async def migrate_hierarchical():
    conn = await asyncpg.connect(DATABASE_URL)
    print("Migrating Database to Hierarchical Multi-Tenancy...")
    
    try:
        async with conn.transaction():
            # 1. Create Organizations Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Insert Default Organization
            await conn.execute("""
                INSERT INTO organizations (name, slug) 
                VALUES ('Default Organization', 'default')
                ON CONFLICT (slug) DO NOTHING;
            """)
            default_org_id = await conn.fetchval("SELECT id FROM organizations WHERE slug = 'default'")

            # 3. Update Users Table
            # Add org_id and change role type if needed
            # Roles: 'super_admin', 'client_admin', 'auditor'
            await conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id)")
            await conn.execute(f"UPDATE users SET org_id = {default_org_id} WHERE org_id IS NULL")
            await conn.execute("UPDATE users SET role = 'super_admin' WHERE username = 'admin'") # Promote initial admin
            
            # 4. Update Other Core Tables with org_id
            tables_to_update = ['cases', 'legal_holds', 'retention_policies', 'audit_logs']
            for table in tables_to_update:
                await conn.execute(f"ALTER TABLE table_placeholder ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id)".replace('table_placeholder', table))
                await conn.execute(f"UPDATE table_placeholder SET org_id = {default_org_id} WHERE org_id IS NULL".replace('table_placeholder', table))

            # 5. Create Sidecar Agents Table (System-wide monitoring)
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

            print("Migration successful! Hierarchy established.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_hierarchical())
