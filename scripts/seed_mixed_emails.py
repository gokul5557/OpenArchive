import smtplib
import random
import time
import os
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate

# Configuration
SMTP_HOST = "127.0.0.1"
SMTP_PORT = 2525
COUNT = 50
ATTACHMENT_CHANCE = 0.3 # 30%

SENDERS = ["gokul@sagasoft.io", "devteam@sagasoft.io", "hr@sagasoft.io", "legal@sagasoft.io"]
RECIPIENT = "archive@archive.local" # Catch-all

SUBJECTS = [
    "Project Update: Phase {i}",
    "Invoice #{rn}",
    "Contract Draft v{rn}",
    "Meeting Minutes ({date})",
    "Security Audit Report",
    "Employee Handbook 2026",
    "Urgent: System Alert {rn}",
    "Welcome Aboard!",
    "Q1 Financials",
    "Design Assets"
]

def generate_attachment():
    """Generates a dummy attachment content and filename."""
    types = [
        ("report.txt", b"Confidential Report Content\nData: " + os.urandom(50)),
        ("invoice.csv", b"Item,Cost\nServer,1000\nLicense,500"),
        ("notes.md", b"# Meeting Notes\n- Action Item 1\n- Action Item 2"),
        ("config.json", b'{"setting": "enabled", "version": 2}')
    ]
    name, content = random.choice(types)
    # Add random suffix to make hash unique
    name = f"{uuid.uuid4().hex[:4]}_{name}"
    return name, content

def send_mixed_emails():
    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT}...")
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        
        for i in range(1, COUNT + 1):
            sender = random.choice(SENDERS)
            rn = random.randint(100, 999)
            has_attachment = random.random() < ATTACHMENT_CHANCE
            
            subject = random.choice(SUBJECTS).format(i=i, rn=rn, date="2026-01-14")
            
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = RECIPIENT
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = subject
            
            body = f"Hello,\n\nThis is email #{i}.\nStatus: {'Has Attachment' if has_attachment else 'Text Only'}.\n\nRegards,"
            msg.attach(MIMEText(body, 'plain'))
            
            if has_attachment:
                fname, content = generate_attachment()
                part = MIMEApplication(content, Name=fname)
                part['Content-Disposition'] = f'attachment; filename="{fname}"'
                msg.attach(part)
                print(f"[{i}/{COUNT}] Sending with attachment: {fname}")
            else:
                print(f"[{i}/{COUNT}] Sending text only.")

            server.sendmail(sender, RECIPIENT, msg.as_string())
            time.sleep(0.1) 

        server.quit()
        print("\n✅ Seeding Complete!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_mixed_emails()
