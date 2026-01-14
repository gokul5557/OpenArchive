import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

def send_cas_email():
    sender = "test@cas.com"
    recipient = "journal@domain1.com"
    
    msg = MIMEMultipart()
    msg['Subject'] = "CAS Deduplication Test"
    msg['From'] = sender
    msg['To'] = recipient
    
    msg.attach(MIMEText("This email contains an attachment that should be deduplicated.", "plain"))
    
    # Create valid PDF content (simple header)
    filename = "test_doc.pdf"
    content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n..." * 100 # Make it somewhat unique/large
    
    part = MIMEBase('application', 'pdf')
    part.set_payload(content)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={filename}')
    msg.attach(part)
    
    print("Sending email to Port 2526...")
    try:
        with smtplib.SMTP('localhost', 2526) as server:
            server.set_debuglevel(1)
            server.sendmail(sender, [recipient], msg.as_string())
        print("Email Sent.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send_cas_email()
