import imaplib
import email
from config import Config

def get_latest_alert():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
    mail.select("inbox")
    
    _, data = mail.search(None, '(FROM "noreply@tradingview.com")')
    latest_email_id = data[0].split()[-1]
    
    _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode()
    return msg.get_payload(decode=True).decode()

def parse_alert(email_body):
    if "Buy" in email_body:
        return 'long'
    elif "Sell" in email_body:
        return 'short'
    return None
