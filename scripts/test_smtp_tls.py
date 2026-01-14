import smtplib
from email.mime.text import MIMEText
import ssl

def send_test_email_tls():
    sender = "test@external.com"
    recipient = "journal@domain1.com"
    body = "This is a SECURE test email sent via SMTP Ingestion (STARTTLS)."
    
    msg = MIMEText(body)
    msg['Subject'] = "SMTP Ingestion SECURE Test"
    msg['From'] = sender
    msg['To'] = recipient
    
    print("Connecting to SMTP (localhost:2525) with TLS...")
    try:
        # Create unverified context (since self-signed)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with smtplib.SMTP('localhost', 2526) as server:
            server.set_debuglevel(1)
            server.ehlo()
            if server.has_extn('STARTTLS'):
                print("Server supports STARTTLS. Securing connection...")
                server.starttls(context=context)
                server.ehlo() # Re-identify after encrypted session
                print("Connection Secured.")
            else:
                print("WARNING: Server did NOT advertise STARTTLS!")
            
            server.sendmail(sender, [recipient], msg.as_string())
        print("Secure Email Sent Successfully.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    send_test_email_tls()
