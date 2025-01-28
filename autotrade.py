import time
import re
import requests
from imapclient import IMAPClient
import email
from email.policy import default
import logging
from flask import Flask, jsonify
import threading

# Set up logging configuration to show detailed debug information
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app initialization
app = Flask(__name__)

# Alpaca API credentials
ALPACA_API_URL = "https://paper-api.alpaca.markets/v2"
ALPACA_API_KEY = "PKCCAHDTUSPTYNMRQBA2"
ALPACA_SECRET_KEY = "Peh8XoPBwmgrxxfPvGKO5F8SnfHZt6lVsybUJ8qy"

# Email credentials
EMAIL = "jtmendescb@gmail.com"
PASSWORD = "pkdj ptea aioo wqfy"
IMAP_SERVER = "imap.gmail.com"  # e.g., imap.gmail.com

# Function to connect to your email and fetch unread emails
def fetch_alert_emails():
    try:
        logging.info('Connecting to email server...')
        with IMAPClient(IMAP_SERVER) as client:
            client.login(EMAIL, PASSWORD)
            client.select_folder("INBOX")
            logging.info('Searching for unread emails...')
            messages = client.search([
                "UNSEEN",
                "FROM", "noreply@tradingview.com",
                "SUBJECT", "guito"  # Replace with your actual subject line
            ])
            emails = []
            logging.info(f'Found {len(messages)} unread emails.')
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
                    logging.info('Fetched email content.')
                client.set_flags(msg_id, [r'\Seen'])
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

# Place a trade (buy/sell) using Alpaca API
def place_trade(symbol, side, qty=0.014):
    endpoint = f"{ALPACA_API_URL}/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
    }

    # Ensure the side is either "buy" or "sell"
    if side.lower() not in ["buy", "sell"]:
        logging.error(f"Invalid side: {side}")
        return None

    order = {
        "symbol": symbol,
        "qty": qty,
        "side": side,  # Ensure it's in lowercase
        "type": "market",
        "time_in_force": "gtc"
    }

    try:
        # Send the POST request to place the order
        response = requests.post(endpoint, json=order, headers=headers)

        # Check the HTTP status code
        if response.status_code == 200:
            logging.info(f"Order placed successfully: {response.json()}")
            return response.json()  # This should work if the response is valid JSON
        else:
            logging.error(f"Failed to place order. Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during request: {e}")
        return None

# Function to continuously check for new emails
def continuous_email_check():
    while True:
        try:
            logging.info("Starting email check loop...")
            emails = fetch_alert_emails()
            trades = []
            logging.info(f"Checking {len(emails)} email(s) for trade signals.")
            for email_content in emails:
                trade_data = parse_email(email_content)
                if trade_data:
                    action = trade_data["action"]
                    symbol = trade_data["symbol"]
                    if action in ['buy', 'sell']:
                        result = place_trade(symbol, action)  # "buy" or "sell" will be passed here
                        trades.append({"symbol": symbol, "action": action, "result": result})
                    else:
                        logging.warning(f"Invalid action found in email: {action}")
            if trades:
                logging.info(f"Trade(s) executed: {trades}")
            else:
                logging.info("No valid trades found in emails.")
        except Exception as e:
            logging.error(f"Error during email checking: {e}")

        # Wait for 60 seconds before checking for new emails
        time.sleep(60)

# Flask route to trigger email checking and trade placement manually
@app.route('/trigger', methods=['GET'])
def trigger_email_check():
    try:
        emails = fetch_alert_emails()
        trades = []
        logging.info(f"Checking {len(emails)} email(s) for trade signals.")
        for email_content in emails:
            trade_data = parse_email(email_content)
            if trade_data:
                action = trade_data["action"]
                symbol = trade_data["symbol"]
                if action in ['buy', 'sell']:
                    result = place_trade(symbol, action)  # "buy" or "sell" will be passed here
                    trades.append({"symbol": symbol, "action": action, "result": result})
                else:
                    logging.warning(f"Invalid action found in email: {action}")
        if trades:
            return jsonify({"message": "Trade(s) executed", "trades": trades}), 200
        else:
            logging.info("No valid trades found in emails.")
            return jsonify({"message": "Email check complete, no trades found", "trades": []}), 200
    except Exception as e:
        logging.error(f"Error during trigger: {e}")
        return jsonify({"error": str(e)}), 500

# Flask route to check if the service is running
@app.route('/')
def home():
    return jsonify({"message": "Service is running"}), 200

if __name__ == "__main__":
    # Start the email checking loop in a background thread
    email_thread = threading.Thread(target=continuous_email_check)
    email_thread.daemon = True  # Ensures the thread stops when the main program exits
    email_thread.start()

    # Start the Flask server
    app.run(host='0.0.0.0', port=5000)

