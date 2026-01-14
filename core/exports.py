
import os
import zipfile
import io
import time
from datetime import datetime
from email.message import EmailMessage
from email.policy import default
from cryptography.fernet import Fernet
from fpdf import FPDF
import mailbox
import search
import storage
import redaction

# Temporary directory for exports (could be S3 in production)
EXPORT_DIR = "/tmp/exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

import re
import base64

def generate_eml(metadata, decrypted_body):
    """
    Reconstructs the original EML object from the stripped source (decrypted_body),
    re-hydrating any CAS-stripped attachments.
    """
    import email
    from email import encoders
    
    # Parse as legacy Message (more reliable for surgical re-hydration)
    msg = email.message_from_string(decrypted_body)
    
    # Iterate and re-hydrate
    for part in msg.walk():
        # Check for CAS Header
        cas_ref = part.get("X-OpenArchive-CAS-Ref")
        if not cas_ref:
            # Check for placeholder in payload if header missing
            payload = part.get_payload()
            if isinstance(payload, str) and "[CAS_REF:" in payload:
                match = re.search(r"\[CAS_REF:(.*?)\]", payload)
                if match:
                    cas_ref = match.group(1)

        if cas_ref:
            cas_hash = cas_ref.strip()
            blob_data = storage.get_blob(f"cas_{cas_hash}.enc")
            
            if blob_data:
                # Re-attach content
                part.set_payload(blob_data)
                
                # Encode as base64 and wrap lines correctly
                encoders.encode_base64(part)
                
                # Force visibility by setting name and filename
                filename = part.get_filename() or part.get_param("name", header="Content-Type")
                if not filename:
                    # Fallback filename
                    filename = f"attachment_{cas_hash[:8]}"
                    
                # Set name in Content-Type (important for many viewers)
                part.set_param("name", filename, header="Content-Type")
                
                # Set/Update Content-Disposition to attachment to force visibility
                if "Content-Disposition" in part:
                    part.set_param("filename", filename, header="Content-Disposition")
                    # If it was inline, many viewers hide it from attachment list. 
                    # For forensic export, we often want it visible.
                    cd = part.get("Content-Disposition", "")
                    if "inline" in cd.lower():
                        part.replace_header("Content-Disposition", f'attachment; filename="{filename}"')
                else:
                    part.add_header("Content-Disposition", "attachment", filename=filename)

                # Remove the CAS ref header to make it look "original"
                if "X-OpenArchive-CAS-Ref" in part:
                    del part["X-OpenArchive-CAS-Ref"]
            else:
                print(f"Export Warning: Missing CAS blob {cas_hash}")
                
    return msg

def clean_text(text):
    """Clean text for PDF rendering (remove non-latin characters if font issue)"""
    # FPDF standard font (Courier/Arial) handles limited charset. 
    # For now, let's encode/decode ascii to avoid crashes, or replace.
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_pdf(metadata, decrypted_body, bates_number):
    """Generates a PDF content bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    
    # Header
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(0, 10, f"Bates: {bates_number}", ln=True, align='R')
    pdf.ln(5)
    
    effective_width = pdf.epw
    label_w = 30
    value_w = effective_width - label_w
    
    def print_field(label, value):
        pdf.set_font("Courier", 'B', 10)
        pdf.cell(label_w, 6, f"{label}:", ln=False)
        
        pdf.set_font("Courier", '', 10)
        pdf.multi_cell(value_w, 6, clean_text(value))

    print_field("From", metadata.get('from', ''))
    print_field("To", metadata.get('to', ''))
    print_field("Date", str(metadata.get('date', '')))
    print_field("Subject", metadata.get('subject', ''))
    
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    # Body
    pdf.set_font("Courier", '', 10)
    pdf.multi_cell(0, 5, clean_text(decrypted_body))
    
    return pdf.output(dest='S')
    
async def create_export_job(export_id: str, items: list, format: str = "native", redact: bool = False):
    """
    Background Task to process export.
    items: list of {message_id, tag?}
    format: 'native' (zip of emls) or 'pdf' (zip of pdfs)
    """
    
    zip_filename = f"{export_id}.zip"
    zip_path = os.path.join(EXPORT_DIR, zip_filename)
    
    # Fetch all details from Meili Search first
    # Or fetch one by one? One by one is slower but safer for memory.
    # Or batched.
    
    try:
        mbox_path = None
        if format == 'mbox':
            mbox_path = os.path.join(EXPORT_DIR, f"{export_id}.mbox")
            mbox = mailbox.mbox(mbox_path)
            mbox.lock()

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            
            # Fetch Metadata
            # We need keys. Search result includes 'key'.
            ids = [i['message_id'] for i in items]
            
            # Meili Filter limit? We might have 1000s.
            # Batch fetch 100 at a time.
            chunk_size = 100
            for k in range(0, len(ids), chunk_size):
                chunk_ids = ids[k:k+chunk_size]
                
                # Fetch Metada & Keys
                quoted_ids = [f'"{mid}"' for mid in chunk_ids]
                id_list_str = ', '.join(quoted_ids)
                id_filter = f"id IN [{id_list_str}]"
                results = search.search_documents(query="", filter_query=id_filter, limit=chunk_size)
                hits = {h['id']: h for h in results.get('hits', [])}
                
                for mid in chunk_ids:
                    meta = hits.get(mid)
                    if not meta:
                        continue
                        
                    key = meta.get('key')
                    if not key:
                        continue
                        
                    # Fetch Blob
                    blob_enc = storage.get_blob(f"{mid}.enc")
                    if not blob_enc:
                        continue
                        
                    # Decrypt
                    try:
                        cipher = Fernet(key.encode()) # Key stored as string in Meili?
                        decrypted_body = cipher.decrypt(blob_enc).decode('utf-8')
                        
                        if redact:
                            decrypted_body = redaction.redact_text(decrypted_body)
                            meta['subject'] = redaction.redact_text(meta.get('subject', ''))
                            meta['from'] = redaction.redact_text(meta.get('from', ''))
                            meta['to'] = redaction.redact_text(meta.get('to', ''))
                        
                        if format == 'native':
                            eml = generate_eml(meta, decrypted_body)
                            # Ensure proper CRLF and MIME formatting for standard viewers
                            from email.generator import BytesGenerator
                            fp = io.BytesIO()
                            gen = BytesGenerator(fp, mangle_from_=False, maxheaderlen=78)
                            gen.flatten(eml)
                            zf.writestr(f"{mid}.eml", fp.getvalue())
                            
                        elif format == 'pdf':
                            pdf_bytes = generate_pdf(meta, decrypted_body, mid)
                            zf.writestr(f"{mid}.pdf", pdf_bytes)
                        elif format == 'mbox':
                            eml = generate_eml(meta, decrypted_body)
                            # Convert EmailMessage to mbox Message
                            msg = mailbox.mboxMessage(eml.as_bytes())
                            mbox.add(msg)
                            
                    except Exception as e:
                        print(f"Error processing {mid}: {e}")
                        if format != 'mbox':
                            zf.writestr(f"{mid}_error.txt", str(e))
                        else:
                            # For mbox, maybe add a dummy message with error?
                            pass
            
            if format == 'mbox':
                mbox.flush()
                mbox.unlock()
                mbox.close()
                if os.path.exists(mbox_path):
                    zf.write(mbox_path, f"{export_id}.mbox")
                    os.remove(mbox_path)
                        
        return zip_path
        
    except Exception as e:
        print(f"Export Job Failed: {e}")
        return None
