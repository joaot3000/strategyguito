import logging
import re
import os
from imapclient import IMAPClient
import email
from email.policy import default
from telegram import Bot
from flask import Flask, jsonify
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler

# Set up logging configuration to show detailed debug information
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app initialization
app = Flask(__name__)

# Email credentials
EMAIL = os.getenv("EMAIL", "jtmendescb@gmail.com")
PASSWORD = os.getenv("EMAIL_PASSWORD", "pkdj ptea aioo wqfy")
IMAP_SERVER = "imap.gmail.com"  # e.g., imap.gmail.com

# Telegram Bot credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7897853987:AAEVLNuZxCWT8CmzqszUf9sJ5PdLfNq4vLg")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5825643489")

# Initialize Telegram Bot
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Function to send Telegram messages
def send_telegram_message(message):
    try:
        telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

# Function to connect to your email and fetch unread emails
def fetch_alert_emails():
    try:
        logging.info('Connecting to email server...')
        with IMAPClient(IMAP_SERVER) as client:
            client.login(EMAIL, PASSWORD)
            client.select_folder("INBOX")
            logging.info('Searching for unread emails...')
            messages = client.search([
                "UNSEEN",  # Fetch unread messages
                "FROM", "noreply@tradingview.com",  # Sender email address
                "SUBJECT", "guito"  # Subject filter (adjust as needed)
            ])
            if not messages:
                logging.info("No unread emails matching criteria found.")
            emails = []
            for msg_id, data in client.fetch(messages, "RFC822").items():
                msg = email.message_from_bytes(data[b"RFC822"], policy=default)
                email_content = None
                if msg.is_multipart():
                    for part in msg.iter_parts():
                        logging.debug(f'Part content type: {part.get_content_type()}')
                        if part.get_content_type() in ["text/plain", "text/html"]:
                            email_content = part.get_payload(decode=True).decode('utf-8')
                            logging.debug(f'Fetched email part: {email_content}')
                            break
                else:
                    if msg.get_content_type() in ["text/plain", "text/html"]:
                        email_content = msg.get_payload(decode=True).decode('utf-8')
                        logging.debug(f'Fetched email content: {email_content}')
                if email_content:
                    emails.append(email_content)
                    logging.info('Fetched email content successfully.')
                client.set_flags(msg_id, [r'\Seen'])  # Mark email as read
            return emails
    except Exception as e:
        logging.error(f"Failed to fetch emails: {e}")
        return []

# Parse the email content to extract action and symbol
def parse_email(content):
    logging.debug(f"Parsing email content: {content}")  # Log email content to verify
    action_match = re.search(r"Action[:\s]*(buy|sell)", content, re.IGNORECASE)
    symbol_match = re.search(r"Symbol[:\s]*([A-Za-z0-9/-]+)", content, re.IGNORECASE)
    
    if action_match and symbol_match:
        logging.info(f"Parsed action: {action_match.group(1)}, symbol: {symbol_match.group(1)}")
        return {
            "action": action_match.group(1).lower(),  # Store the action as "buy" or "sell" (in lowercase)
            "symbol": symbol_match.group(1).upper()   # Symbol should be uppercase (e.g., BTC/USD)
        }
    else:
        logging.warning("No action or symbol found in the email content.")
    return None

def check_emails_periodically():
    logging.info("Checking for new emails...")
    emails = fetch_alert_emails()  # This will fetch unread emails
    if emails:
        logging.info(f"Found {len(emails)} new emails.")
        for email_content in emails:
            trade_data = parse_email(email_content)  # Parse email for trade signal
            if trade_data:
                action = trade_data["action"]
                symbol = trade_data["symbol"]
                logging.info(f"Parsed action: {action} for symbol: {symbol}")
                # Send Telegram message
                send_telegram_message(f"New email read: {action} {symbol}")
    else:
        logging.info("No new emails found.")

# Now, set the scheduler to run the check_emails_periodically() every 10 seconds
scheduler = BackgroundScheduler()
scheduler.add_job(check_emails_periodically, 'interval', seconds=10)  # Run every 10 seconds
scheduler.start()

# Flask route to trigger email checking
@app.route('/trigger', methods=['GET'])
def trigger_email_check():
    try:
        emails = fetch_alert_emails()
        if emails:
            return jsonify({"message": "Emails read", "emails": emails}), 200
        else:
            return jsonify({"message": "No new emails found"}), 200
    except Exception as e:
        logging.error(f"Error during trigger: {e}")
        return jsonify({"error": str(e)}), 500

# Flask route to check if the service is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Service is running"}), 200

# Run the Flask app
def main():
    """Run the bot.""" 
    # Start Flask app in background 
    def run_flask():
        app.run(host='0.0.0.0', port=5000)

    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True  # Daemonize thread
    flask_thread.start()

if __name__ == "__main__":
    main()
