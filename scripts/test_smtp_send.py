import smtplib
from email.mime.text import MIMEText

def send_test_email():
    sender = "test@external.com"
    recipient = "journal@domain1.com" # Should map to Org 8 (domain1.com)
    body = "This is a test email sent via SMTP Ingestion."
    
    msg = MIMEText(body)
    msg['Subject'] = "SMTP Ingestion Test"
    msg['From'] = sender
    msg['To'] = recipient
    
    print("Connecting to SMTP (localhost:2525)...")
    try:
        with smtplib.SMTP('localhost', 2525) as server:
            server.set_debuglevel(1)
            server.sendmail(sender, [recipient], msg.as_string())
        print("Email Sent Successfully.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    send_test_email()
