import asyncio
import os
import random
import uuid
import json
from datetime import datetime, timedelta
import sys

# Add core to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../core'))

import database
import search
import integrity
# Mock security hash to avoid importing passlib if complex, 
# but we can try importing security if installed.
try:
    import security
    def get_hash(pwd): return security.get_password_hash(pwd)
except ImportError:
    # Fallback if security setup fails in script env
    def get_hash(pwd): return f"mock_hash_{pwd}"

# Configuration
SEED_PASSWORD = os.getenv("SEED_PASSWORD", "password")
NUM_ORGS = 5
DOMAINS_TOTAL = 15
EMAILS_PER_DOMAIN = 20

async def main():
    print("Connecting to DB...")
    conn = await database.get_db_connection()
    
    try:
        # 1. Create Organizations & Domains
        orgs = []
        domains_pool = [f"domain{i}.com" for i in range(1, DOMAINS_TOTAL + 1)]
        
        print(f"Creating {NUM_ORGS} Organizations with distributed domains...")
        
        for i in range(1, NUM_ORGS + 1):
            name = f"Organization {i}"
            slug = f"org-{i}"
            
            # Distribute 3 domains per org
            start = (i-1) * 3
            end = start + 3
            org_domains = domains_pool[start:end]
            
            # Check if exists
            exists = await conn.fetchval("SELECT id FROM organizations WHERE slug = $1", slug)
            if not exists:
                org_id = await conn.fetchval(
                    "INSERT INTO organizations (name, slug, domains) VALUES ($1, $2, $3) RETURNING id",
                    name, slug, org_domains
                )
                print(f"Created {name} (ID: {org_id}) with domains: {org_domains}")
            else:
                org_id = exists
                # Update domains just in case
                await conn.execute("UPDATE organizations SET domains = $1 WHERE id = $2", org_domains, org_id)
                print(f"Updated {name} (ID: {org_id}) domains.")
            
            orgs.append({"id": org_id, "name": name, "domains": org_domains})

        # 2. Create Users (Client Admin & Auditors)
        print("Creating Users...")
        for org in orgs:
            oid = org['id']
            odoms = org['domains']
            
            # Client Admin
            ca_user = f"admin_org{oid}"
            exists = await conn.fetchval("SELECT 1 FROM users WHERE username = $1", ca_user)
            if not exists:
                await conn.execute(
                    "INSERT INTO users (username, role, org_id, domains, password_hash) VALUES ($1, $2, $3, $4, $5)",
                    ca_user, "client_admin", oid, json.dumps(odoms), get_hash(SEED_PASSWORD)
                )
                print(f"  Created Client Admin: {ca_user} / {SEED_PASSWORD}")

            # Auditor 1 (All domains)
            aud1 = f"auditor_org{oid}_1"
            if not await conn.fetchval("SELECT 1 FROM users WHERE username = $1", aud1):
                await conn.execute(
                    "INSERT INTO users (username, role, org_id, domains, password_hash) VALUES ($1, $2, $3, $4, $5)",
                    aud1, "auditor", oid, json.dumps(odoms), get_hash(SEED_PASSWORD)
                )
                print(f"  Created Auditor: {aud1} (All Domains)")

            # Auditor 2 (Subset: First domain only)
            aud2 = f"auditor_org{oid}_2"
            if not await conn.fetchval("SELECT 1 FROM users WHERE username = $1", aud2):
                await conn.execute(
                    "INSERT INTO users (username, role, org_id, domains, password_hash) VALUES ($1, $2, $3, $4, $5)",
                    aud2, "auditor", oid, json.dumps([odoms[0]]), get_hash(SEED_PASSWORD)
                )
                print(f"  Created Auditor: {aud2} (Domain: {odoms[0]})")

        # 3. Generate Dummy Emails
        print("Generating Emails & Indexing...")
        documents = []
        
        for org in orgs:
            oid = org['id']
            for domain in org['domains']:
                print(f"  Generating emails for {domain}...")
                for _ in range(EMAILS_PER_DOMAIN):
                    emsg_id = str(uuid.uuid4())
                    sender = f"user{random.randint(1,100)}@{domain}"
                    
                    # Random recipient (mostly internal or other known domains)
                    target_domain = random.choice(domains_pool)
                    recipient = f"contact@{target_domain}"
                    
                    subject = f"Business update regarding {random.choice(['Project X', 'Q1 Report', 'Audit', 'Compliance'])}"
                    body = "This is a dummy email body generated for testing purposes. " * 5
                    
                    dt = (datetime.utcnow() - timedelta(days=random.randint(0, 30)))
                    
                    doc = {
                        'id': emsg_id,
                        'message_id': f"<{uuid.uuid4()}@{domain}>",
                        'from': sender,
                        'to': recipient,
                        'subject': subject,
                        'date': dt.isoformat(),
                        'date_timestamp': int(dt.timestamp()),
                        'body': body,
                        'org_id': oid, # Multi-tenancy
                        'domains': [domain, target_domain], # Involved domains
                        'sender_domain': domain,
                        'recipient_domains': [target_domain],
                        'has_attachments': False,
                        'is_spam': False,
                        'size': len(body)
                    }
                    documents.append(doc)
        
        # Batch Indexing
        if documents:
            search.index_documents(documents)
            print(f"Indexed {len(documents)} emails to MeiliSearch.")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
