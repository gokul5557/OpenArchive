import asyncio
import os
# from dotenv import load_dotenv
# load_dotenv()

import uuid
import logging
from email import message_from_bytes
from email.policy import default
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult
from crypto import generate_key, encrypt_data
from buffer import init_db, save_message
import pdfplumber
import io
import pytesseract
from PIL import Image
import hashlib
from buffer import init_db, save_message, save_cas_blob

# Configure Logging
# Configure Logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OpenArchiveSidecar")
logger.info(f"Logging initialized at level: {log_level}")

class ArchiveHandler:
    async def handle_DATA(self, server, session, envelope):
        try:
            logger.info("Received message from: %s", envelope.mail_from)
            
            # 1. Generate ID and Key
            msg_id = str(uuid.uuid4())
            key = generate_key()
            
            # 2. Parse Headers for Metadata
            raw_data = envelope.content
            msg = message_from_bytes(raw_data, policy=default)
            
            # Helper to extract IDs from Message-ID / References headers
            def extract_ids(header_val):
                if not header_val: return []
                # Remove quotes and split by whitespace
                return [val.strip() for val in str(header_val).split() if val.strip()]

            # Helper for PDF/Image text extraction
            def extract_attachment_text(part):
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                text = ""
                
                try:
                    if content_type == 'application/pdf':
                        with pdfplumber.open(io.BytesIO(payload)) as pdf:
                            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    elif content_type.startswith('image/'):
                        # requires system tesseract-ocr
                        img = Image.open(io.BytesIO(payload))
                        text = pytesseract.image_to_string(img)
                    elif content_type == 'text/plain':
                        text = payload.decode('utf-8', errors='replace')
                except Exception as e:
                    logger.warning(f"Error extracting text from {content_type}: {e}")
                
                return text.strip()


            attachment_data = []
            has_attachments = False
            cas_refs = []

            # Walk parts for CAS extraction
            # We must be careful not to break the iterator if we modify in place?
            # Safe to modify content.
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                    
                if part.get_content_disposition() == 'attachment' or part.get_filename():
                    has_attachments = True
                    payload = part.get_payload(decode=True)
                    
                    if payload:
                        # 1. OCR / Text Extraction (Keep existing logic)
                        extracted_text = extract_attachment_text(part)
                        if extracted_text:
                            attachment_data.append({
                                "filename": part.get_filename(),
                                "content_type": part.get_content_type(),
                                "text": extracted_text
                            })
                        
                        # 2. CAS Deduplication
                        sha256 = hashlib.sha256(payload).hexdigest()
                        
                        # Save to Local CAS Buffer
                        # We use encrypt_data on this payload? 
                        # Ideally, CAS blobs should be encrypted.
                        # Using independent key? Or Master Key?
                        # If we use Convergent Encryption (Hash=Key), we need no extra key storage.
                        # But here, we are just buffering. 
                        # Let's simple-store raw bytes in buffer, and Sync will handle encryption/upload?
                        # Wait, Sync upload uses `upload_blob` which Encrypts!
                        # `upload_cas_blobs` inside `main.py` -> `storage.upload_blob` -> `encryption.encrypt_data`.
                        # So we send Plaintext to Core?
                        # `sync.py` sends `base64` of file content.
                        # If we store Plaintext in `buffer.db`, it's insecure on Agent disk?
                        # Agent has `crypto.encrypt_data`.
                        # If we encrypt with Random Key, we break Deduplication on Core (Ciphertext unique).
                        # We MUST send Plaintext to Core (via TLS) and let Core encrypt (using Master Key)?
                        # OR Core uses Convergent Encryption.
                        # To keep it simple currently:
                        # 1. Store Plaintext in Agent Buffer (Assuming Agent is secure env / temp).
                        # 2. Sync sends Plaintext.
                        # 3. Core Encrypts.
                        # Security Check: At rest in Agent? `buffer.db` has `storage_path`.
                        # If we want Agent-side encryption, we must use Convergent Key.
                        # Let's stick to Plaintext buffering for MVP Deduplication.
                        
                        await save_cas_blob(sha256, payload)
                        cas_refs.append(sha256)
                        
                        # 3. Strip Payload from Message to save space
                        part.set_payload(f"[CAS_REF:{sha256}]")
                        del part['Content-Transfer-Encoding'] # Reset encoding since we are now text
                        part.add_header('X-OpenArchive-CAS-Ref', sha256)

            metadata = {
                "from": msg.get("From"),
                "to": msg.get("To"),
                "subject": msg.get("Subject"),
                "date": msg.get("Date"),
                "message_id": msg.get("Message-ID"),
                "in_reply_to": extract_ids(msg.get("In-Reply-To")),
                "references": extract_ids(msg.get("References")),
                "envelope_from": envelope.mail_from,
                "envelope_rcpt": envelope.rcpt_tos,
                "size": len(raw_data), # Original size
                "has_attachments": has_attachments,
                "cv_attachments": cas_refs, # Track refs
                "attachment_content": " ".join([a['text'] for a in attachment_data]) if attachment_data else ""
            }
            
            # Serialize Modified Message (Skeleton)
            raw_data = msg.as_bytes()
            
            # 3. Encrypt Body
            encrypted_blob = encrypt_data(raw_data, key)
            
            logger.info(f"Extracted metadata: {metadata}")
            
            # 4. Save to Buffer
            await save_message(msg_id, key, metadata, encrypted_blob)
            
            logger.info(f"✅ RECEIVED EMAIL | ID: {msg_id} | Subject: '{metadata['subject']}' | From: {metadata['from']} | To: {metadata['to']} | Size: {metadata['size']} bytes")
            return '250 OK'
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return '451 Internal Server Error'

class DummyAuthenticator:
    def __call__(self, server, session, envelope, mechanism, auth_data):
        # Accept any username/password for internal network compatibility
        return AuthResult(success=True)

async def start_agent():
    # Initialize DB
    await init_db()
    
    # Start SMTP Controller
    port = int(os.getenv("SMTP_PORT", 2525))
    handler = ArchiveHandler()
    # Adding authenticator to avoid "Unsupported Authentication Mechanism" in Stalwart
    # Explicitly enable PLAIN and LOGIN mechanisms
    controller = Controller(
        handler, 
        hostname='0.0.0.0', 
        port=port, 
        authenticator=DummyAuthenticator(),
        auth_require_tls=False
    )
    # Ensure mechanisms are enabled on the server instance
    # Controller uses the SMTP class by default.
    controller.start()
    
    logger.info("OpenArchive Sidecar listening on 0.0.0.0:2525")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Stopping Sidecar...")
        controller.stop()

if __name__ == "__main__":
    asyncio.run(start_agent())
