import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

SMTP_HOST = "127.0.0.1"
SMTP_PORT = 2525
SENDER = "gokul@sagasoft.io"
RECIPIENT = "auditor@sagasoft.xyz"

def send_with_attachment():
    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT}...")
    
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = RECIPIENT
    msg['Subject'] = "Test Email with Attachment"
    
    # Body
    msg.attach(MIMEText("This email contains a test attachment.", 'plain'))
    
    # Attachment
    filename = "test_doc.txt"
    content = b"This is the content of the attached file.\nIt serves as a test for the archive system."
    
    part = MIMEApplication(content, Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)
    
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())
        server.quit()
        print("Email with attachment sent successfully!")
    except Exception as e:
        print(f"Failed to send: {e}")

if __name__ == "__main__":
    send_with_attachment()
