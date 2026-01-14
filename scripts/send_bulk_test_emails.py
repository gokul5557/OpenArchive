import smtplib
import random
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

# Configuration
# SMTP_HOST = "mail.sagasoft.io"
# SMTP_PORT = 587
# Target Local Sidecar Agent directly to bypass remote rate limits
SMTP_HOST = "127.0.0.1" 
SMTP_PORT = 2525
SMTP_USER = "test" # Dummy auth accepted by agent
SMTP_PASS = "test"

TARGET_EMAIL = "gokul@sagasoft.xyz"

# Senders to alternate
SENDERS = [
    "gokul@sagasoft.io",
    "devteam@sagasoft.io"
]

# Random subjects to make it look real
SUBJECT_TEMPLATES = [
    "Project Update: Phase {i}",
    "Invoice #{rn} for Consultation",
    "Weekly Report - Week {i}",
    "Urgent: Server Alert {rn}",
    "Meeting Notes: {i}/01/2026",
    "Welcome to the team!",
    "Security Alert: Login attempt {rn}",
    "Quarterly Review Q{i}",
    "Feedback on Design #{rn}",
    "Deployment Status: Success ({rn})"
]

def send_bulk_emails(count=100):
    print(f"Connecting to {SMTP_HOST}...")
    
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        # server.starttls() # Not needed for local agent
        server.login(SMTP_USER, SMTP_PASS)
        print("Logged in successfully.")

        for i in range(1, count + 1):
            sender = random.choice(SENDERS)
            rn = random.randint(1000, 9999)
            subject = random.choice(SUBJECT_TEMPLATES).format(i=i, rn=rn)
            
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = TARGET_EMAIL
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = subject

            body = f"""
            Hello,

            This is test email #{i} sent from {sender}.
            Random ID: {rn}

            Regards,
            Automated Test Script
            """
            msg.attach(MIMEText(body, 'plain'))

            server.sendmail(sender, TARGET_EMAIL, msg.as_string())
            print(f"[{i}/{count}] Sent: '{subject}' from {sender}")
            
            # Sleep slightly to avoid strict rate limits if any
            time.sleep(0.2)

        server.quit()
        print("\nAll emails sent successfully!")

    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    send_bulk_emails()
