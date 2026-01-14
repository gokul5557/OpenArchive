# Reload Trigger 1
from fastapi import FastAPI, Depends, HTTPException, Header, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
import base64
import os
import json

load_dotenv()
import storage
import search
import admin
import database
import cases
import exports
import threads
import redaction
import integrity
import integrity
import security
import retention_worker
import integrity_worker
import smtp_server
import analytics
import asyncio

app = FastAPI(title="OpenArchive Core API")

@app.get("/api/v1/admin/analytics")
async def get_admin_analytics(org_id: int):
    return await analytics.get_org_analytics(org_id)

# Configure Logging
import logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OpenArchiveCore")
logger.info(f"Logging initialized at level: {log_level}")

@app.on_event("startup")
async def startup_db_client():
    await database.connect()
    # Ensure tables exist
    await database.create_tables()
    # Migration: Add domains to organizations if not exists
    try:
        # await database.database.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS domains TEXT[] DEFAULT '{}'")
        pass
    except Exception as e:
        print(f"Migration warning: {e}")
    
    
    # Start Retention Worker (Background Loop)
    asyncio.create_task(retention_worker.start_worker())
    
    # Start Integrity Worker (Background Loop)
    asyncio.create_task(integrity_worker.start_worker())
    
    # Start SMTP Server (Port 2525)
    smtp_server.start_smtp_server()

@app.on_event("shutdown")
async def shutdown_db_client():
    await database.disconnect()

    # Initialize Search

app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])

API_KEY = os.getenv("CORE_API_KEY", "secret")

class SyncItem(BaseModel):
    id: str
    key: str
    metadata: Dict[str, Any]
    blob_b64: str

class SyncBatch(BaseModel):
    batch: List[SyncItem]

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/v1/auth/login")
async def login(creds: LoginRequest):
    # 1. Hardcoded Super Admin (bootstrap)
    if creds.username == "admin" and creds.password == "admin":
        return {"id": 1, "username": "admin", "role": "super_admin", "org_id": 1, "domains": []}

    # 2. Database Lookup
    conn = await database.get_db_connection()
    try:
        user = await conn.fetchrow("SELECT * FROM users WHERE username = $1", creds.username)
        if user:
            # 3. Verify Password
            if not user['password_hash']:
                # Migration: Allow any password if hash missing? 
                # Or block? For transition, if you created user without pass, we might need a way to set it.
                # But my 'create_user' forces password now.
                # For old users (if any), they can't login unless we check plain password match (if we stored plain? No).
                # We assume new users have hash.
                pass 
                # Fail open or closed? Closed for security.
                # But wait, user asked "In admin client admin creation set password there".
                # If hash is null, maybe fail.
            elif not security.verify_password(creds.password, user['password_hash']):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            user_data = {
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "org_id": user['org_id'],
                "domains": json.loads(user['domains']) if user['domains'] else []
            }
            
            # 4. Create Token
            token = security.create_access_token(data={"sub": user['username'], "role": user['role'], "id": user['id']})
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": user_data
            }
        
        raise HTTPException(status_code=401, detail="Invalid credentials")
    finally:
        await conn.close()

@app.post("/api/v1/sync")
async def sync_messages(payload: SyncBatch, x_api_key: str = Header(None), x_org_id: int = Header(1)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    successful_ids = []
    documents_to_index = []
    
    for item in payload.batch:
        try:
            # 1. Decode Blob
            blob_data = base64.b64decode(item.blob_b64)
            
            # 2. Upload to Storage
            object_name = f"{item.id}.enc"
            if storage.upload_blob(object_name, blob_data):
                successful_ids.append(item.id)
                
                # 3. Prepare Metadata for Indexing
                doc = item.metadata
                doc['id'] = item.id
                doc['key'] = item.key 
                
                # MULTI-TENANT RESOLUTION
                # 1. Extract Domains
                domain_set = set()
                def extract_all_domains(email_val):
                    if not email_val: return
                    if isinstance(email_val, list):
                        for e in email_val: extract_all_domains(e)
                    elif isinstance(email_val, str):
                        if "@" in email_val:
                            d = email_val.split("@")[-1].strip().lower().rstrip('>')
                            domain_set.add(d)
                
                extract_all_domains(doc.get('from'))
                extract_all_domains(doc.get('to'))
                extract_all_domains(doc.get('envelope_from'))
                extract_all_domains(doc.get('envelope_rcpt'))
                
                # 2. Query DB for matching Orgs
                # Using a fresh connection for this request
                domain_list = list(domain_set)
                resolved_org_ids = []
                
                try:
                    conn = await database.get_db_connection()
                    try:
                        # Find orgs where any of the email domains exist in the organization's 'domains' array
                        # Postgres overlap operator: domains && ARRAY[...]
                        q = "SELECT id FROM organizations WHERE domains && $1" 
                        rows = await conn.fetch(q, domain_list)
                        resolved_org_ids = [r['id'] for r in rows]
                    finally:
                        await conn.close()
                except Exception as e:
                    print(f"Error resolving orgs: {e}")

                # 3. Fallback to Default Org (1) if no resolution (or x_org_id if explicitly provided as fallback)
                if not resolved_org_ids:
                    resolved_org_ids = [1]
                    
                doc['org_id'] = resolved_org_ids # Now a LIST of integers
                
                # CRYPTOGRAPHIC INTEGRITY
                doc['sha256'] = integrity.calculate_hash(blob_data)
                doc['signature'] = integrity.sign_data(blob_data)
                
                # Robust email address extraction
                def extract_email(email_str):
                    if not email_str: return None
                    import re
                    # Handle "Name <email@domain.com>"
                    match = re.search(r'<(.+?)>', email_str)
                    if match: return match.group(1).lower().strip()
                    # Handle "email@domain.com"
                    if '@' in email_str: return email_str.strip().lower()
                    return None

                # Robust domain extraction
                def extract_domain(email_str):
                    email = extract_email(email_str)
                    if email:
                        return email.split('@')[-1]
                    return None

                # Indexing clean emails for Legal Holds
                recipient_emails = set()
                
                # Header From
                doc['sender_email'] = extract_email(doc.get('from'))
                # Header To
                to_val = doc.get('to')
                if to_val:
                    if isinstance(to_val, list):
                        for t in to_val:
                            e = extract_email(t)
                            if e: recipient_emails.add(e)
                    else:
                        e = extract_email(to_val)
                        if e: recipient_emails.add(e)
                
                # Envelope Overwrites/Additions
                env_from = extract_email(doc.get('envelope_from'))
                if env_from:
                    doc['sender_email'] = env_from
                
                env_rcpts = doc.get('envelope_rcpt')
                if env_rcpts:
                    for r in env_rcpts:
                        e = extract_email(r)
                        if e: recipient_emails.add(e)
                
                doc['recipient_emails'] = list(recipient_emails)

                # EXTRACT DOMAINS for Multi-Tenancy Filtering
                domains = set()
                recipient_domains = set()
                sender_domain = None

                # Check headers
                s_dom = extract_domain(doc.get('from'))
                if s_dom: 
                    sender_domain = s_dom
                    domains.add(s_dom)
                
                r_dom = extract_domain(doc.get('to'))
                if r_dom:
                    recipient_domains.add(r_dom)
                    domains.add(r_dom)
                
                # Check envelope (more reliable)
                env_s_dom = extract_domain(doc.get('envelope_from'))
                if env_s_dom:
                    sender_domain = env_s_dom # Envelope sender is more authoritative
                    domains.add(env_s_dom)
                    
                if doc.get('envelope_rcpt'):
                    for rcpt in doc['envelope_rcpt']:
                        rd = extract_domain(rcpt)
                        if rd:
                            recipient_domains.add(rd)
                            domains.add(rd)
                
                # Remove None and convert to list
                doc['domains'] = list(filter(None, domains))
                doc['sender_domain'] = sender_domain
                doc['recipient_domains'] = list(filter(None, recipient_domains))

                # SORTING: Add date_timestamp for Meilisearch sorting
                import email.utils
                date_str = doc.get('date')
                if date_str:
                    try:
                        dt = email.utils.parsedate_to_datetime(date_str)
                        doc['date_timestamp'] = int(dt.timestamp())
                    except Exception as e:
                        print(f"Warning: Failed to parse date '{date_str}': {e}")
                        doc['date_timestamp'] = 0
                else:
                    doc['date_timestamp'] = 0
                
                # print(f"DEBUG: Ingesting {item.id} | Timestamp: {doc['date_timestamp']} | Domains: {doc['domains']}")
                
                documents_to_index.append(doc)
            else:
                print(f"Failed to upload blob for {item.id}")
                
        except Exception as e:
            print(f"Error processing item {item.id}: {e}")

    # 4. Batch Index
    if documents_to_index:
        search.index_documents(documents_to_index)
        
    return {"status": "ok", "processed": len(successful_ids)}

class CASCheckRequest(BaseModel):
    hashes: List[str]

@app.post("/api/v1/cas/check")
async def check_cas_availability(req: CASCheckRequest, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        print(f"AUTH FAIL: Received='{x_api_key}' Expected='{API_KEY}'")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    result = {}
    for h in req.hashes:
        # Check existence of Encrypted Blob for this hash
        # Key Pattern: cas_{hash}.enc
        exists = storage.blob_exists(f"cas_{h}.enc")
        result[h] = exists
    return result

class CASUploadItem(BaseModel):
    hash: str
    blob_b64: str

class CASUploadBatch(BaseModel):
    batch: List[CASUploadItem]

@app.post("/api/v1/cas/upload")
async def upload_cas_blobs(payload: CASUploadBatch, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    saved = 0
    for item in payload.batch:
        blob_data = base64.b64decode(item.blob_b64)
        object_name = f"cas_{item.hash}.enc"
        if storage.upload_blob(object_name, blob_data):
            saved += 1
            
    return {"status": "ok", "saved": saved}

@app.get("/api/v1/messages")
async def search_messages(
    org_id: int,
    q: str = "", 
    limit: int = 20,
    offset: int = 0,
    user_domain: str = None,
    from_addr: str = None,
    to_addr: str = None,
    date_start: str = None,
    date_end: str = None,
    has_attachments: bool = None,
    is_spam: bool = None,
    direction: str = None, # 'sent', 'received', 'internal'
    attachment_keyword: str = None
):
    # Build filter query
    # org_id in Meilisearch is now an ARRAY of integers.
    # To strict-filter by current user's org_id, we check if user's org_id IN doc.org_id
    filters = [f"org_id = {org_id}"] # Meilisearch automatically handles 'value IN array_field'

    
    
    
    # DB Connection for Org Domain Lookup & Legal Holds
    conn = await database.get_db_connection()
    try:
        if user_domain:
            # Core restriction: Document must involve ONE of the user's domains
            # Support comma-separated list
            raw_domains = [d.strip() for d in user_domain.split(',') if d.strip()]
            
            # EXPAND: If a domain belongs to the Org, allow access to ALL Org domains (Domain Aliasing)
            try:
                org_domains_raw = await conn.fetchval("SELECT domains FROM organizations WHERE id = $1", org_id)
                org_domains = set(org_domains_raw) if org_domains_raw else set()
                
                expanded_domains = set(raw_domains)
                if not org_domains.isdisjoint(expanded_domains):
                     expanded_domains.update(org_domains)
                
                u_domains = list(expanded_domains)
            except Exception as e:
                print(f"Error expanding domains: {e}")
                u_domains = raw_domains
            
            if u_domains:
                domain_filters = [f"domains = '{d}'" for d in u_domains]
                filters.append(f"({' OR '.join(domain_filters)})")

        
        # Directional logic relative to user_domain(s) - Complex for multiple
        # For now, if multiple domains, simplify direction logic or apply to all
        if direction:
             if direction == 'sent':
                 # sender_domain IN [d1, d2]
                 sd_filters = [f"sender_domain = '{d}'" for d in u_domains]
                 filters.append(f"({' OR '.join(sd_filters)})")
             elif direction == 'received':
                 # recipient_domains matches ANY
                 # recipient_domains = 'd1' OR recipient_domains = 'd2' - strictly checks containment
                 rd_filters = [f"recipient_domains = '{d}'" for d in u_domains]
                 filters.append(f"({' OR '.join(rd_filters)})")
             elif direction == 'internal':
                 # Both sender && recipient in allowed list
                 # (sender_domain IN u_domains) AND (recipient_domains IN u_domains)
                 sd_filters = [f"sender_domain = '{d}'" for d in u_domains]
                 rd_filters = [f"recipient_domains = '{d}'" for d in u_domains]
                 filters.append(f"({' OR '.join(sd_filters)}) AND ({' OR '.join(rd_filters)})")
    
        if from_addr:
            if not q: q = from_addr
            else: q = f"{q} {from_addr}"
            
        if to_addr:
             if not q: q = to_addr
             else: q = f"{q} {to_addr}"
    
        if has_attachments is not None:
            filters.append(f"has_attachments = {str(has_attachments).lower()}")
            
        if is_spam is not None:
            filters.append(f"is_spam = {str(is_spam).lower()}")
    
        if date_start:
             filters.append(f"date >= {date_start}")
             
        if date_end:
             filters.append(f"date <= {date_end}")
    
        if attachment_keyword:
            if not q:
                q = attachment_keyword
            else:
                q = f"{q} {attachment_keyword}"
    
        filter_query = " AND ".join(filters) if filters else None
        
        results = search.search_documents(q, limit, filter_query, offset)
        
        # Check for Legal Holds on results
        if results and results.get('hits'):
            # 1. Get all held message IDs for this org
            held_ids = await conn.fetch("SELECT message_id FROM legal_hold_items i JOIN legal_holds h ON i.hold_id = h.id WHERE h.org_id = $1", org_id)
            held_set = {r['message_id'] for r in held_ids}
            
            # 2. Get all held "Accounts" (criteria-based) for this org
            active_holds = await conn.fetch("SELECT filter_criteria FROM legal_holds WHERE active = TRUE AND org_id = $1", org_id)
            held_from = set()
            held_to = set()
            held_keywords = set()
            for h in active_holds:
                crit = json.loads(h['filter_criteria'])
                if crit.get('from'): held_from.add(crit['from'])
                if crit.get('to'): held_to.add(crit['to'])
                if crit.get('q'): held_keywords.add(crit['q'].lower())

            for hit in results['hits']:
                # Clean email checks are most reliable
                s_email = hit.get('sender_email')
                r_emails = hit.get('recipient_emails', [])
                
                # Expose clean emails for UI
                hit['sender_email_clean'] = s_email
                hit['recipient_emails_clean'] = r_emails
                
                # Keyword match (heuristic for UI badge)
                kw_match = False
                if held_keywords:
                    search_blob = f"{hit.get('subject','')} {hit.get('from','')} {hit.get('to','')}".lower()
                    if any(kw in search_blob for kw in held_keywords):
                        kw_match = True

                hit['is_on_hold'] = (
                    hit['id'] in held_set or 
                    s_email in held_from or 
                    any(r in held_to for r in r_emails) or
                    hit.get('from') in held_from or 
                    hit.get('to') in held_to or
                    kw_match
                )
    finally:
        await conn.close()
            
    return results

@app.get("/api/v1/messages/{id}")
async def get_message(id: str, org_id: int):
    # 1. Fetch encrypted blob
    blob_enc = storage.get_blob(f"{id}.enc")
    if not blob_enc:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # 2. Decrypt (Server-side implementation for MVP)
    # Note: In a real "Unbreakable" system, we might return the encrypted blob 
    # and let the client decrypt if they have the method. 
    # For this MVP, we will attempt to find the key.
    # Earlier we decided NOT to store the key in MinIO. 
    # We indexed it in Meilisearch (risky but functional for MVP).
    
    # Fetch metadata to get key
    # We can use the check_known_id of meilisearch or just search helper
    # Since meilisearch search is fast, we filter by ID
    
    try:
        index = search.client.index('emails')
        doc = index.get_document(id)
        
        # Verify org_id in document
        doc_org_id = getattr(doc, 'org_id', None) or doc.get('org_id')
        
        # Determine access
        has_access = False
        if isinstance(doc_org_id, list):
            if org_id in doc_org_id: has_access = True
        elif doc_org_id == org_id:
            has_access = True
            
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this message")

        try:
            # Try attribute access for newer meilisearch client
            key = getattr(doc, 'key', None)
        except AttributeError:
            # Fallback for dict
            key = doc.get('key')

        
        if not key:
             raise HTTPException(status_code=500, detail="Encryption key not found")
             
        from cryptography.fernet import Fernet
        f = Fernet(key.encode('utf-8'))
        decrypted_blob = f.decrypt(blob_enc)
        
        # Parse to return something friendly? or just raw?
        # Let's return the raw bytes but maybe as text if possible
        # Or simple JSON wrapper
        
        # RE-HYDRATION LOGIC (CAS Deduplication)
        try:
            decoded_content = decrypted_blob.decode('utf-8', errors='replace')
            
            # Check for CAS Reference Pattern: [CAS_REF:<sha256>]
            import re
            cas_matches = re.findall(r'\[CAS_REF:([a-fA-F0-9]{64})\]', decoded_content)
            
            if cas_matches:
                for cas_hash in cas_matches:
                    print(f"DEBUG: Found CAS Ref {cas_hash} in message {id}")
                    # Fetch CAS Blob (Storage handles Master Key decryption automatically)
                    cas_blob = storage.get_blob(f"cas_{cas_hash}.enc")
                    
                    if cas_blob:
                        # Replace the placeholder with the actual content
                        # Assuming CAS blob is text (email body). If binary, this might need handling.
                        # For now, we assume text extraction logic in Agent implies text.
                        try:
                            replacement_text = cas_blob.decode('utf-8', errors='replace')
                            decoded_content = decoded_content.replace(f"[CAS_REF:{cas_hash}]", replacement_text)
                        except Exception as e:
                             print(f"Error decoding CAS blob {cas_hash}: {e}")
                    else:
                        print(f"Warning: CAS Blob {cas_hash} not found.")

            # IMPROVED RETURN WITH BODY PARSING
            # Now parse the EML to extract the actual body for the UI
            import email
            import email.policy
            
            try:
                msg_obj = email.message_from_string(decoded_content, policy=email.policy.default)
                body_text = ""
                body_html = ""
                attachments = []
                inline_images = {} # Map Content-ID -> Base64

                for part in msg_obj.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get("Content-Disposition", ""))
                    cid = part.get("Content-ID", "").strip("<>")
                    
                    # Check for CAS Reference
                    cas_ref = part.get("X-OpenArchive-CAS-Ref")
                    payload = None
                    
                    if cas_ref:
                        cas_hash = cas_ref.strip()
                        blob_data = storage.get_blob(f"cas_{cas_hash}.enc")
                        if blob_data:
                            print(f"DEBUG: Re-hydrated CAS Attachment {cas_hash} ({len(blob_data)} bytes)")
                            payload = blob_data
                        else:
                            print(f"Warning: CAS Attachment Blob {cas_hash} not found.")
                            # Fallback if possible. Check if it is multipart before calling get_content
                            if not part.is_multipart():
                                payload = part.get_content()
                    else:
                        if not part.is_multipart():
                            try:
                                payload = part.get_content()
                            except Exception as e:
                                print(f"Warning: Failed to get content for part {ctype}: {e}")
                                payload = part.get_payload(decode=True) # Fallback to raw payload

                    is_attachment = "attachment" in cdispo or (cid and not ctype.startswith("text"))
                    
                    if is_attachment:
                        b64_payload = None
                        
                        if payload is None:
                            continue # Skip if no payload found

                        if isinstance(payload, bytes):
                            b64_payload = base64.b64encode(payload).decode('utf-8')
                        elif isinstance(payload, str):
                             b64_payload = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
                        elif isinstance(payload, list) or hasattr(payload, 'as_bytes'):
                            # Handle message/rfc822 or other objects
                             try:
                                 raw = payload.as_bytes()
                                 b64_payload = base64.b64encode(raw).decode('utf-8')
                             except:
                                 # Fallback for complex objects
                                 try:
                                     raw = str(payload).encode('utf-8')
                                     b64_payload = base64.b64encode(raw).decode('utf-8')
                                 except: pass

                        if b64_payload:
                            # If it has a CID, store for substitution
                            if cid:
                                inline_images[cid] = f"data:{ctype};base64,{b64_payload}"
                            
                            # Also list as regular attachment if it has a filename or is an attachment
                            filename = part.get_filename()
                            if filename or "attachment" in cdispo:
                                attachments.append({
                                    "filename": filename or f"attachment_{len(attachments)+1}.{ctype.split('/')[-1]}",
                                    "content_type": ctype,
                                    "size": len(b64_payload), # Approx size
                                    "content_b64": b64_payload
                                })
                    else:
                        # Body Parts
                        if ctype == "text/plain" and "attachment" not in cdispo:
                            if payload and isinstance(payload, str):
                                body_text += payload
                            elif payload and isinstance(payload, bytes):
                                body_text += payload.decode('utf-8', errors='replace')
                        elif ctype == "text/html" and "attachment" not in cdispo:
                             if payload and isinstance(payload, str):
                                body_html += payload
                             elif payload and isinstance(payload, bytes):
                                body_html += payload.decode('utf-8', errors='replace')

                # Fix Inline Images in HTML
                if body_html and inline_images:
                    for cid, data_uri in inline_images.items():
                        body_html = body_html.replace(f"cid:{cid}", data_uri)

                # Prioritize HTML for "content_html" and Text for "content" (fallback)
                final_content = body_text or body_html or decoded_content
                
                return {
                    "id": id,
                    "content": final_content, # Legacy/Text
                    "content_html": body_html,
                    "attachments": attachments,
                    "raw_eml": decoded_content # Full source
                }
                
            except Exception as parsing_error:
                print(f"EML Parsing failed: {parsing_error}")
                # Fallback to raw string
                return {
                    "id": id, 
                    "content": decoded_content,
                    "raw_eml": decoded_content
                }

        except Exception as e:
             # Fallback for binary/failed decode
             print(f"Re-hydration failed or binary content: {e}")
             return {"id": id, "content_b64": base64.b64encode(decrypted_blob).decode('utf-8')}
             
    except HTTPException:
        raise
    except Exception as e:
        print(f"Decryption error: {e}")
        raise HTTPException(status_code=500, detail="Decryption failed")

@app.get("/api/v1/messages/{id}/headers")
async def get_message_headers_endpoint(id: str, org_id: int):
    msg = await get_message_content(id, org_id)
    raw_eml = msg.get("raw_eml", "")
    if not raw_eml:
        return []
        
    import email, email.policy
    try:
            # Parse just headers
            msg_obj = email.message_from_string(raw_eml, policy=email.policy.default)
            return [{"name": k, "value": str(v)} for k, v in msg_obj.items()]
    except:
            return []

@app.get("/api/v1/messages/{id}/thread")
async def get_message_thread(id: str, org_id: int):
    # threads.get_thread might need org_id awareness too, but for MVP let's assume get_message base logic is enough
    # Actually threads should also be org-scoped.
    return threads.get_thread(id, org_id)

@app.get("/api/v1/messages/{id}/preview-redacted")
async def preview_redacted_message(id: str, org_id: int):
    msg = await get_message(id, org_id)
    content = msg.get("content") or (base64.b64decode(msg["content_b64"]).decode('utf-8') if msg.get("content_b64") else "")
    entities = redaction.identify_pii(content)
    return {
        "id": id,
        "original": content,
        "redacted": redaction.redact_text(content),
        "entities": entities
    }

@app.get("/api/v1/messages/{id}/pii-scan")
async def scan_message_pii(id: str, org_id: int):
    msg = await get_message(id, org_id)
    content = msg.get("content") or (base64.b64decode(msg["content_b64"]).decode('utf-8') if msg.get("content_b64") else "")
    entities = redaction.identify_pii(content)
    return {
        "id": id,
        "pii_detected": len(entities) > 0,
        "entities": entities
    }

@app.get("/api/v1/messages/{id}/verify")
async def verify_message_integrity(id: str, org_id: int):
    # 1. Fetch encrypted blob
    blob_enc = storage.get_blob(f"{id}.enc")
    if not blob_enc:
        return {"id": id, "verified": False, "error": "Blob not found"}
        
    # 2. Fetch metadata (signature)
    try:
        index = search.client.index('emails')
        doc = index.get_document(id)
        
        # Verify org
        doc_org_id = getattr(doc, 'org_id', None) or doc.get('org_id')
        if doc_org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        signature = getattr(doc, 'signature', None) or doc.get('signature')
        
        if not signature:
             return {"id": id, "status": "UNAVAILABLE", "verified": False, "error": "Signature not found in metadata"}
             
        # 3. Verify
        is_valid = integrity.verify_integrity(blob_enc, signature)
        return {
            "id": id,
            "status": "VALID" if is_valid else "TAMPERED",
            "verified": is_valid,
            "hash": integrity.calculate_hash(blob_enc),
            "stored_signature": signature
        }
    except Exception as e:
        return {"id": id, "status": "ERROR", "verified": False, "error": str(e)}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/downloads/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(exports.EXPORT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
