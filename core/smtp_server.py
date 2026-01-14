import asyncio
import logging
import email
import json
import os
import email
import json
from email import policy
from datetime import datetime
import uuid
import database
import storage
import search
import integrity

try:
    from aiosmtpd.controller import Controller
    from aiosmtpd.handlers import AsyncMessage
except ImportError:
    Controller = None
    AsyncMessage = object

logger = logging.getLogger("SMTPServer")

ALLOWED_IPS = os.getenv("ALLOWED_SMTP_IPS", "127.0.0.1").split(",")

class ArchiveHandler(AsyncMessage):
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        # IP Whitelisting
        peer_ip = session.peer[0]
        if peer_ip not in ALLOWED_IPS:
            logger.warning(f"SMTP Access Denied for IP: {peer_ip}")
            return "550 Access Denied"
        
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_message(self, message):
        """
        Processed incoming SMTP message.
        message: email.message.Message object (parsed)
        """
        try:
            # 1. Identify Tenant via Recipient
            # Logic: Check all recipients. If any matches an Org domain, archive for that Org.
            # Real world: Journaling usually sends to one specific address.
            recipients = message.get_all('To', []) + message.get_all('Cc', []) + message.get_all('Bcc', []) # header recipients
            # Actual envelope recipients are tricky in AsyncMessage handle_message unless we use handle_DATA with envelope.
            # But let's assume specific routing logic or just header analysis for MVP.
            
            # Better: Map ALL domains in recipients to Orgs.
            conn = await database.get_db_connection()
            try:
                # Cache org domains? For now query.
                rows = await conn.fetch("SELECT id, domains FROM organizations")
                
                target_orgs = set()
                
                # Extract domains from message
                msg_domains = set()
                
                # Address parsing (simplistic)
                for addr in recipients:
                     if '@' in str(addr):
                         dom = str(addr).split('@')[-1].strip().lower().strip('>')
                         msg_domains.add(dom)
                
                # Check envelope recipients if possible (requires handle_DATA override), but message headers usually suffice for journaling.
                
                for row in rows:
                    org_doms = set(row['domains']) # Expected list
                    # Intersection
                    if not msg_domains.isdisjoint(org_doms):
                        target_orgs.add(row['id'])

                if not target_orgs:
                    logger.warning(f"SMTP: No matching organization for domains {msg_domains}. Dropping.")
                    return
                
                # 2. Archive for each Target Org
                # Current architecture: Single storage, multiple indices? 
                # Or one index with org_id.
                # If email belongs to multiple Orgs (e.g. Org A -> Org B), do we duplicate?
                # Multi-tenancy usually implies shared storage or duplicate?
                # For `org_id` filtering, we need creating multiple index entries OR one entry with multiple org_ids?
                # MeiliSearch schema: `org_id` is INT. 
                # So we must duplicate the INDEX entry for each Org, but Storage can be shared (Content Addressable?).
                # My storage uses `id.enc`. `id` is UUID.
                # If I use content-hash as ID, I can de-duplicate.
                # But current logic uses random UUID.
                
                blob_data = message.as_bytes()
                sha_hash = integrity.calculate_hash(blob_data)
                
                for oid in target_orgs:
                    msg_id = str(uuid.uuid4())
                    object_name = f"{msg_id}.enc"
                    
                    # Upload (if exists, overwrite is fine)
                    storage.upload_blob(object_name, blob_data)
                    
                    # Metadata
                    # Body Extraction
                    body = ""
                    try:
                        if message.is_multipart():
                            for part in message.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body += payload.decode('utf-8', errors='ignore')
                        else:
                            payload = message.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                    except Exception as e:
                        logger.warning(f"Body extract failed: {e}")

                    doc = {
                        'id': msg_id,
                        'message_id': message.get('Message-ID', ''),
                        'from': message.get('From', ''),
                        'to': message.get('To', ''),
                        'subject': message.get('Subject', ''),
                        'date': message.get('Date') or datetime.utcnow().isoformat(),
                        'date_timestamp': int(datetime.utcnow().timestamp()), # Approximation if parsing fails
                        'body': body,
                        'org_id': oid,
                        'has_attachments': bool(message.iter_attachments()) if hasattr(message, 'iter_attachments') else False,
                        'sha256': sha_hash,
                        'signature': integrity.sign_data(blob_data),
                        'domains': list(msg_domains) # Indexed domains for search
                    }
                    
                    search.index_documents([doc])
                    
                    # Audit Log
                    # Bypass RLS? Yes, raw connection used.
                    # We need to INSERT to audit_logs.
                    # RLS might block if we don't set context correctly.
                    # But if we use 'super_admin' or just raw check.
                    # Insert policy might require org_id match.
                    # Let's set context.
                    await conn.execute(f"SELECT set_config('app.current_org_id', '{oid}', false)")
                    await conn.execute("SELECT set_config('app.current_role', 'client_admin', false)")
                    
                    # Calculate hashes for audit (using admin logic simplified)
                    details = {"source": "SMTP", "size": len(blob_data)}
                    details_str = json.dumps(details, sort_keys=True)
                    last_hash = await conn.fetchval("SELECT current_hash FROM audit_logs WHERE org_id = $1 ORDER BY id DESC LIMIT 1", oid) or "ROOT_HASH"
                    payload = f"{last_hash}systemSMTP{details_str}{oid}"
                    curr_hash = integrity.calculate_hash(payload.encode())
                    
                    await conn.execute("""
                        INSERT INTO audit_logs (org_id, username, action, details, previous_hash, current_hash)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, oid, "system", "SMTP_INGEST", details_str, last_hash, curr_hash)
                    
                    logger.info(f"Archived SMTP message {msg_id} for Org {oid}")

            except Exception as e:
                logger.error(f"SMTP Processing Error: {e}")
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Handler Error: {e}")

import ssl

def start_smtp_server(port=2525):
    if not Controller:
        logger.error("aiosmtpd not installed. SMTP Server disabled.")
        return
        
    try:
        # Load Certificates for STARTTLS
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile="core/certs/cert.pem", keyfile="core/certs/key.pem")
        
        handler = ArchiveHandler()
        # Controller with ssl_context enables STARTTLS support (advertising it in EHLO)
        controller = Controller(handler, hostname='0.0.0.0', port=port, ssl_context=context)
        controller.start()
        logger.info(f"SMTP Server running on port {port} (STARTTLS enabled)")
        return controller
    except Exception as e:
        logger.error(f"Failed to start SMTP Server: {e}")
