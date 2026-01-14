from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import database
import json
import search
import json
import search
import integrity
import json
import search
import integrity
import security
import retention_worker

router = APIRouter()

# --- Models ---
class OrganizationCreate(BaseModel):
    name: str
    slug: str
    domains: List[str] = []

class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    domains: List[str]
    created_at: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str # 'super_admin', 'client_admin', 'auditor'
    org_id: int
    domains: List[str] = []

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    org_id: int
    domains: List[str]

class AgentResponse(BaseModel):
    id: int
    name: str
    hostname: Optional[str]
    org_id: Optional[int]
    status: str
    last_seen: Optional[str]

class AuditLogCreate(BaseModel):
    username: str
    action: str
    details: Optional[dict] = {}

class AuditLogEntry(AuditLogCreate):
    id: int
    timestamp: str

class LegalHoldCreate(BaseModel):
    name: str
    reason: str
    filter_criteria: dict # e.g. {"domains": ["bad.com"]}

# --- Organization Management (Super Admin) ---

@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations():
    conn = await database.get_db_connection()
    try:
        rows = await conn.fetch("SELECT id, name, slug, domains, timestamp_placeholder as created_at FROM organizations ORDER BY id ASC".replace('timestamp_placeholder', 'created_at'))
        return [
            OrganizationResponse(
                id=r['id'],
                name=r['name'],
                slug=r['slug'],
                domains=r['domains'] if r['domains'] else [],
                created_at=str(r['created_at'])
            ) for r in rows
        ]
    finally:
        await conn.close()

@router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(org: OrganizationCreate):
    conn = await database.get_db_connection()
    try:
        exists = await conn.fetchval("SELECT 1 FROM organizations WHERE slug = $1", org.slug)
        if exists:
            raise HTTPException(status_code=400, detail="Organization slug already exists")

        row = await conn.fetchrow(
            "INSERT INTO organizations (name, slug, domains) VALUES ($1, $2, $3) RETURNING id, name, slug, domains, created_at",
            org.name, org.slug, org.domains
        )
        return OrganizationResponse(
            id=row['id'],
            name=row['name'],
            slug=row['slug'],
            domains=row['domains'] if row['domains'] else [],
            created_at=str(row['created_at'])
        )
    finally:
        await conn.close()

@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: int):
    conn = await database.get_db_connection()
    try:
        # Check if exists
        exists = await conn.fetchval("SELECT 1 FROM organizations WHERE id = $1", org_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Manual Cascade Delete
        await conn.execute("DELETE FROM legal_hold_items WHERE hold_id IN (SELECT id FROM legal_holds WHERE org_id = $1)", org_id)
        await conn.execute("DELETE FROM legal_holds WHERE org_id = $1", org_id)
        await conn.execute("DELETE FROM case_items WHERE case_id IN (SELECT id FROM cases WHERE org_id = $1)", org_id)
        await conn.execute("DELETE FROM cases WHERE org_id = $1", org_id)
        await conn.execute("DELETE FROM audit_logs WHERE org_id = $1", org_id)
        await conn.execute("DELETE FROM retention_policies WHERE org_id = $1", org_id)
        await conn.execute("DELETE FROM sidecar_agents WHERE org_id = $1", org_id)
        await conn.execute("DELETE FROM users WHERE org_id = $1", org_id)
        await conn.execute("DELETE FROM organizations WHERE id = $1", org_id)
        
        return {"status": "deleted"}
    finally:
        await conn.close()

# --- User Management ---

@router.get("/users", response_model=List[UserResponse])
async def list_users(org_id: Optional[int] = Query(None)):
    conn = await database.get_db_connection()
    try:
        query = "SELECT id, username, role, org_id, domains FROM users"
        params = []
        if org_id:
            # Client Admin View: See all users in their org (Auditors)
            query += " WHERE org_id = $1"
            params.append(org_id)
        else:
            # Super Admin View: See ONLY Client Admins
            query += " WHERE role = 'client_admin'"
        
        query += " ORDER BY id ASC"
        
        rows = await conn.fetch(query, *params)
        return [
            UserResponse(
                id=r['id'], 
                username=r['username'], 
                role=r['role'], 
                org_id=r['org_id'],
                domains=json.loads(r['domains'])
            ) for r in rows
        ]
    finally:
        await conn.close()

@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    conn = await database.get_db_connection()
    try:
        # Check if exists
        exists = await conn.fetchval("SELECT 1 FROM users WHERE username = $1", user.username)
        if exists:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Validation: Ensure domains belong to Org
        if user.org_id:
            org_domains = await conn.fetchval("SELECT domains FROM organizations WHERE id = $1", user.org_id)
            if org_domains:
                # org_domains is already a list (TEXT[])
                # Check if subset
                for d in user.domains:
                    if d not in org_domains:
                         raise HTTPException(status_code=400, detail=f"Domain {d} not authorized for this Organization")

        # Hash Password
        hashed_password = security.get_password_hash(user.password)

        row = await conn.fetchrow(
            """
            INSERT INTO users (username, role, org_id, domains, password_hash)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, username, role, org_id, domains
            """,
            user.username, user.role, user.org_id, json.dumps(user.domains), hashed_password
        )
        return UserResponse(
            id=row['id'], 
            username=row['username'], 
            role=row['role'], 
            org_id=row['org_id'],
            domains=json.loads(row['domains'])
        )
    finally:
        await conn.close()

@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    conn = await database.get_db_connection()
    try:
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        return {"status": "deleted"}
    finally:
        await conn.close()


# --- Audit Logs ---

@router.get("/audit-logs", response_model=List[AuditLogEntry])
async def list_audit_logs(org_id: int, limit: int = 50):
    conn = await database.get_db_connection()
    try:
        # RLS Context
        await conn.execute(f"SELECT set_config('app.current_org_id', '{org_id}', false)")
        await conn.execute("SELECT set_config('app.current_role', 'client_admin', false)")

        rows = await conn.fetch("SELECT id, username, action, details, timestamp FROM audit_logs WHERE org_id = $1 ORDER BY timestamp DESC LIMIT $2", org_id, limit)
        return [
            AuditLogEntry(
                id=r['id'],
                username=r['username'],
                action=r['action'],
                details=json.loads(r['details']) if r['details'] else {},
                timestamp=str(r['timestamp'])
            ) for r in rows
        ]
    finally:
        await conn.close()

@router.post("/audit-logs")
async def create_audit_log(entry: AuditLogCreate, org_id: int):
    conn = await database.get_db_connection()
    try:
        # RLS Context
        await conn.execute(f"SELECT set_config('app.current_org_id', '{org_id}', false)")
        await conn.execute("SELECT set_config('app.current_role', 'client_admin', false)")

        # Get the strict JSON string and Timestamp
        last_hash = await conn.fetchval("SELECT current_hash FROM audit_logs WHERE org_id = $1 ORDER BY id DESC LIMIT 1", org_id) or "ROOT_HASH"
        
        # Details should be sorted for stable hashing
        details_str = json.dumps(entry.details, sort_keys=True)
        
        # We won't include the timestamp in the hash if it's generated by DB to avoid drift
        payload = f"{last_hash}{entry.username}{entry.action}{details_str}{org_id}"
        current_hash = integrity.calculate_hash(payload.encode())

        await conn.execute(
            """
            INSERT INTO audit_logs (org_id, username, action, details, previous_hash, current_hash)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            org_id, entry.username, entry.action, details_str, last_hash, current_hash
        )
        return {"status": "logged", "hash": current_hash}
    finally:
        await conn.close()

@router.get("/audit-logs/verify")
async def verify_audit_chain(org_id: int):
    conn = await database.get_db_connection()
    try:
        rows = await conn.fetch("SELECT id, username, action, details, previous_hash, current_hash FROM audit_logs WHERE org_id = $1 ORDER BY id ASC", org_id)
        
        last_hash = "ROOT_HASH"
        for r in rows:
            # 1. Check link
            if r['previous_hash'] != last_hash:
                return {"valid": False, "error": f"Chain broken at ID {r['id']}: Link mismatch."}
            
            # 2. Verify current hash
            details_str = json.dumps(json.loads(r['details']) if r['details'] else {}, sort_keys=True)
            payload = f"{r['previous_hash']}{r['username']}{r['action']}{details_str}{org_id}"
            expected_hash = integrity.calculate_hash(payload.encode())
            
            if r['current_hash'] != expected_hash:
                return {"valid": False, "error": f"Integrity failure at ID {r['id']}: Content mismatch."}
            
            last_hash = r['current_hash']
            
        return {"valid": True, "log_count": len(rows), "head_hash": last_hash}
    finally:
        await conn.close()


class LegalHoldApply(BaseModel):
    hold_id: int
    message_ids: List[str]

# --- Legal Holds ---

@router.get("/holds")
async def list_holds(org_id: int):
    conn = await database.get_db_connection()
    try:
        # Get holds with item counts
        rows = await conn.fetch("""
            SELECT h.public_id as id, h.name, h.reason, h.filter_criteria, h.created_by, h.created_at, h.active, COUNT(i.id) as item_count
            FROM legal_holds h
            LEFT JOIN legal_hold_items i ON h.id = i.hold_id
            WHERE h.org_id = $1
            GROUP BY h.id, h.public_id
            ORDER BY h.created_at DESC
        """, org_id)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@router.post("/holds")
async def create_hold(hold: LegalHoldCreate, org_id: int):
    conn = await database.get_db_connection()
    held_count = 0
    try:
        # Check Uniqueness within org
        exists = await conn.fetchval("SELECT id FROM legal_holds WHERE name = $1 AND org_id = $2", hold.name, org_id)
        if exists:
            raise HTTPException(status_code=400, detail="Legal Hold with this name already exists in your organization")

        # 1. Create the Hold Record
        import uuid
        public_id = str(uuid.uuid4())
        
        row = await conn.fetchrow(
            """
            INSERT INTO legal_holds (org_id, name, reason, filter_criteria, created_by, public_id)
            VALUES ($1, $2, $3, $4, 'admin', $5)
            RETURNING id, public_id
            """,
            org_id, hold.name, hold.reason, json.dumps(hold.filter_criteria), public_id
        )
        hold_id = row['id']
        returned_id = row['public_id']
        
        # 2. If criteria provided, auto-backfill existing messages
        if hold.filter_criteria:
            # Convert hold criteria (e.g. {"from": "x"}) to Meilisearch query
            # Simplistic mapping: assuming criteria keys match Meili attributes
            # For complex queries, we might need a translator.
            # Using search.search_documents with filters.
            
            filter_parts = []
            for k, v in hold.filter_criteria.items():
                # Handling basic equality for now. 
                # e.g. "from": "john@gmail.com" -> "from = 'john@gmail.com'"
                filter_parts.append(f'{k} = "{v}"')
            
            filter_query = " AND ".join(filter_parts)
            
            # Fetch ALL matching docs (up to limit)
            # Default search limit is 20, we need more.
            # Warning: This is a synchronous blocking call if not async.
            # core/search.py functions are synchronous wrapper around meili client.
            # Ideally should be async or background task. For now, doing it inline (limit 1000).
            
            s_res = search.search_documents(
                query="", 
                filter_query=filter_query,
                limit=10000 
            )
            
            hits = s_res.get('hits', [])
            if hits:
                # Bulk Insert
                params = [(hold_id, hit['id']) for hit in hits]
                await conn.executemany(
                    """
                    INSERT INTO legal_hold_items (hold_id, message_id)
                    VALUES ($1, $2)
                    ON CONFLICT (hold_id, message_id) DO NOTHING
                    """,
                    params
                )
                held_count = len(hits)

        return {"status": "created", "id": returned_id, "auto_held_count": held_count}
    finally:
        await conn.close()

@router.get("/holds/{hold_id}")
async def get_hold(hold_id: str, org_id: int):
    conn = await database.get_db_connection()
    try:
        # Lookup by PUBLIC_ID and verify org_id
        hold = await conn.fetchrow("SELECT *, public_id as id FROM legal_holds WHERE public_id = $1 AND org_id = $2", hold_id, org_id)
        if not hold:
            raise HTTPException(status_code=404, detail="Hold not found")
        
        internal_id = hold['id'] 
        # Actually `hold['id']` will depend on column order or be ambiguous if I alias?
        # Let's avoid aliasing in the SELECT * and just grab the internal ID from the 'id' column (int)
        
        internal_id = await conn.fetchval("SELECT id FROM legal_holds WHERE public_id = $1", hold_id)

        # Get Held Items Using Internal ID
        items = await conn.fetch("SELECT message_id, created_at FROM legal_hold_items WHERE hold_id = $1 ORDER BY created_at DESC LIMIT 100", internal_id)
        
        # Enrich with Details from MeiliSearch (optional but good for UI)
        # We can do a 'get_documents' call if the client supports it, or just return IDs.
        # For now, let's just return the IDs and added_at dates. The UI can fetch details or we can do it here.
        # Let's try to fetch details for these specific IDs using a filter query in MeiliSearch.
        
        enriched_items = []
        if items:
            ids = [i['message_id'] for i in items]
            
            # Construct filter: id IN [...]
            # MeiliSearch filter: id IN ["1", "2", ...]
            # Note: IDs must be quoted strings
            ids_list = ', '.join([f'"{mid}"' for mid in ids])
            filter_query = f"id IN [{ids_list}]"
            
            s_res = search.search_documents(query="", filter_query=filter_query, limit=100)
            print(f"DEBUG: Meili Response Hits: {len(s_res.get('hits', []))}")
            
            hits = {h['id']: h for h in s_res.get('hits', [])}
            
            for item in items:
                mid = item['message_id']
                details = hits.get(mid, {})
                # print(f"DEBUG: Details for {mid}: {details}") 
                enriched_items.append({
                    "message_id": mid,
                    "added_at": str(item['created_at']),
                    "subject": details.get('subject', 'Unknown'),
                    "from": details.get('from', 'Unknown'),
                    "date": details.get('date', None)
                })
        
        return {
            "hold": dict(hold),
            "items": enriched_items
        }
    finally:
        await conn.close()

@router.post("/holds/{hold_id}/release")
async def release_hold(hold_id: str, org_id: int):
    conn = await database.get_db_connection()
    try:
        # Check if exists and belongs to org
        exists = await conn.fetchval("SELECT id FROM legal_holds WHERE public_id = $1 AND org_id = $2", hold_id, org_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Hold not found")

        # Deactivate
        await conn.execute("UPDATE legal_holds SET active = FALSE WHERE public_id = $1 AND org_id = $2", hold_id, org_id)
        return {"status": "released", "id": hold_id}
    finally:
        await conn.close()

@router.post("/holds/apply")
async def apply_hold(payload: LegalHoldApply):
    conn = await database.get_db_connection()
    try:
        # Bulk insert message IDs for the hold
        # Use ON CONFLICT DO NOTHING to avoid duplicates
        params = []
        for mid in payload.message_ids:
            params.append((payload.hold_id, mid))
            
        await conn.executemany(
            """
            INSERT INTO legal_hold_items (hold_id, message_id)
            VALUES ($1, $2)
            ON CONFLICT (hold_id, message_id) DO NOTHING
            """,
            params
        )
        return {"status": "applied", "count": len(payload.message_ids)}
    finally:
        await conn.close()


class RetentionPolicyCreate(BaseModel):
    name: str
    domains: List[str]
    retention_days: int
    action: str = 'PERMANENT_DELETE'

# --- Retention Policies ---

@router.post("/retention/run")
async def manual_retention_run():
    await retention_worker.purge_expired_messages()
    return {"status": "Retention worker triggered"}

@router.get("/retention")
async def list_retention_policies(org_id: Optional[int] = Query(None)):
    conn = await database.get_db_connection()
    try:
        if org_id:
            rows = await conn.fetch("SELECT * FROM retention_policies WHERE org_id = $1 ORDER BY created_at DESC", org_id)
        else:
            # Super Admin: Global Rules (where org_id IS NULL)
            rows = await conn.fetch("SELECT * FROM retention_policies WHERE org_id IS NULL ORDER BY created_at DESC")
            
        return [
            {
                **dict(r),
                'domains': json.loads(r['domains'])
            } for r in rows
        ]
    finally:
        await conn.close()

@router.post("/retention")
async def create_retention_policy(policy: RetentionPolicyCreate, org_id: Optional[int] = Query(None)):
    conn = await database.get_db_connection()
    try:
        policy_id = await conn.fetchval(
            """
            INSERT INTO retention_policies (org_id, name, domains, retention_days, action)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            org_id, policy.name, json.dumps(policy.domains), policy.retention_days, policy.action
        )
        return {"status": "created", "id": policy_id}
    finally:
        await conn.close()

@router.get("/stats")
async def get_dashboard_stats(org_id: Optional[int] = Query(None)):
    conn = await database.get_db_connection()
    try:
        if org_id:
            # Client Admin Stats
            # 1. Get Domains for Meili Filter
            domains = await conn.fetchval("SELECT domains FROM organizations WHERE id = $1", org_id)
            filter_query = None
            if domains and len(domains) > 0:
                # domains is TEXT[] -> list
                # Construct OR filter: domains = 'd1' OR domains = 'd2'
                or_parts = [f"domains = '{d}'" for d in domains]
                filter_query = f"({' OR '.join(or_parts)})"
            
            email_stats = search.get_stats(filter_query)
            
            auditor_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE org_id = $1 AND role = 'auditor'", org_id)
            hold_count = await conn.fetchval("SELECT COUNT(*) FROM legal_holds WHERE org_id = $1 AND active = TRUE", org_id)
            case_count = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE org_id = $1 AND status = 'OPEN'", org_id)
            
            return {
                "total_emails": email_stats['total_emails'],
                "active_auditors": auditor_count,
                "active_holds": hold_count,
                "open_cases": case_count,
                "storage_used": "Calculate via Size" # Placeholder
            }
        else:
            # Super Admin Stats
            email_stats = search.get_stats()
            org_count = await conn.fetchval("SELECT COUNT(*) FROM organizations")
            agent_count = await conn.fetchval("SELECT COUNT(*) FROM sidecar_agents WHERE status = 'ONLINE'")
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            return {
                "total_emails": email_stats['total_emails'],
                "total_organizations": org_count,
                "online_agents": agent_count,
                "total_users": user_count
            }
    finally:
        await conn.close()

@router.delete("/retention/{policy_id}")
async def delete_retention_policy(policy_id: int, org_id: Optional[int] = Query(None)):
    conn = await database.get_db_connection()
    try:
        if org_id:
            await conn.execute("DELETE FROM retention_policies WHERE id = $1 AND org_id = $2", policy_id, org_id)
        else:
            await conn.execute("DELETE FROM retention_policies WHERE id = $1 AND org_id IS NULL", policy_id)
        return {"status": "deleted"}
    finally:
        await conn.close()

# --- Agent Monitoring (Super Admin) ---

@router.get("/system/agents", response_model=List[AgentResponse])
async def list_agents():
    conn = await database.get_db_connection()
    try:
        rows = await conn.fetch("SELECT id, name, hostname, org_id, status, last_seen FROM sidecar_agents ORDER BY last_seen DESC NULLS LAST")
        return [
            AgentResponse(
                id=r['id'],
                name=r['name'],
                hostname=r['hostname'],
                org_id=r['org_id'],
                status=r['status'],
                last_seen=str(r['last_seen']) if r['last_seen'] else None
            ) for r in rows
        ]
    finally:
        await conn.close()
