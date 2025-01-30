import time
import re
import logging
import threading
from flask import Flask, jsonify, request
import requests
from imapclient import IMAPClient
import email
from email.policy import default

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app initialization
app = Flask(__name__)

# Alpaca API credentials (change these for Interactive Brokers)
ALPACA_API_URL = "https://paper-api.alpaca.markets/v2"
ALPACA_API_KEY = "YOUR_API_KEY"
ALPACA_SECRET_KEY = "YOUR_SECRET_KEY"

# Email credentials
EMAIL = "your-email@example.com"
PASSWORD = "your-email-password"
IMAP_SERVER = "imap.gmail.com"

# Function to connect to your email and fetch unread emails
def fetch_alert_emails():
    logging.info('Connecting to email server...')
    with IMAPClient(IMAP_SERVER) as client:
        client.login(EMAIL, PASSWORD)
        client.select_folder("INBOX")
        logging.info('Searching for unread emails...')
        messages = client.search([
            "UNSEEN",
            "FROM", "noreply@tradingview.com",
            "SUBJECT", "guito"
        ])
        emails = []
        logging.info(f'Found {len(messages)} unread emails.')
        for msg_id, data in client.fetch(messages, "RFC822").items():
            msg = email.message_from_bytes(data[b"RFC822"], policy=default)
            email_content = None
            if msg.is_multipart():
                for part in msg.iter_parts():
                    logging.info(f'Part content type: {part.get_content_type()}')
                    if part.get_content_type() in ["text/plain", "text/html"]:
                        email_content = part.get_payload(decode=True).decode('utf-8')
                        logging.info(f'Fetched email part: {email_content}')
                        break
            else:
                if msg.get_content_type() in ["text/plain", "text/html"]:
                    email_content = msg.get_payload(decode=True).decode('utf-8')
                    logging.info(f'Fetched email content: {email_content}')
            if email_content:
                emails.append(email_content)
                logging.info('Fetched email content.')
            client.set_flags(msg_id, [r'\Seen'])
        return emails

# Background task to check for emails and process trades
def background_task():
    while True:
        try:
            emails = fetch_alert_emails()
            trades = []
            for email_content in emails:
                trade_data = parse_email(email_content)
                if trade_data:
                    action = trade_data["action"]
                    symbol = trade_data["symbol"]
                    if action in ['buy', 'sell']:
                        result = process_trade(symbol, action)  # Process the trade
                        trades.append({"symbol": symbol, "action": action, "result": result})
            time.sleep(40)  # Wait 40 seconds before checking again
        except Exception as e:
            logging.error(f"Error in background task: {e}")
            time.sleep(40)  # Wait before retrying if an error occurs

# Start the background task in a separate thread
@app.before_first_request
def start_background_task_thread():
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()

# Your other Flask routes (e.g., health check, trigger, etc.) go here

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


