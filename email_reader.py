import imaplib
import email
from email.header import decode_header
import logging
from config import Config

def get_latest_alert():
    try:
        mail = imaplib.IMAP4_SSL(Config.IMAP_SERVER)
        mail.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
        mail.select("inbox")
        
        _, msgnums = mail.search(None, "UNSEEN")
        if msgnums[0]:
            latest_id = msgnums[0].split()[-1]
            _, data = mail.fetch(latest_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            return msg.get_payload()
        return None
    except Exception as e:
        logging.error(f"Email Error: {str(e)}")
        return None

def parse_alert(email_body):
    # Implement your alert parsing logic
    if "BUY" in email_body:
        return "buy"
    elif "SELL" in email_body:
        return "sell"
    return None
