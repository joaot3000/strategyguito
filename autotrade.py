import time
import re
import logging
from flask import Flask, jsonify, request
import threading
from ib_insync import IB, Stock, MarketOrder

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app initialization
app = Flask(__name__)

# Interactive Brokers API credentials and connection details
IBKR_HOST = '127.0.0.1'
IBKR_PORT = 7497  # Default for paper trading
IBKR_CLIENT_ID = 1  # Use an appropriate client ID for your session

# Email credentials
EMAIL = "jtmendescb@gmail.com"
PASSWORD = "pkdj ptea aioo wqfy"
IMAP_SERVER = "imap.gmail.com"  # e.g., imap.gmail.com

# Initialize the IBKR client
ib = IB()

# Connect to IBKR API (you may need IB Gateway or TWS running)
def connect_ibkr():
    try:
        logging.info("Attempting to connect to IBKR API...")
        ib.connect(IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID)
        logging.info("Successfully connected to IBKR API.")
    except Exception as e:
        logging.error(f"Error connecting to IBKR API: {e}")

def disconnect_ibkr():
    if ib.isConnected():
        ib.disconnect()
        logging.info("Disconnected from IBKR API")

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
            "SUBJECT", "guito"  # Replace with your actual subject line
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

def parse_email(content):
    # Extract action (buy/sell) and symbol from the email content
    action_match = re.search(r"Action: (buy|sell)", content, re.IGNORECASE)
    symbol_match = re.search(r"Symbol: ([A-Z]+(?:/[A-Z]+)?)", content, re.IGNORECASE)
    
    # If both action and symbol are found, return them
    if action_match and symbol_match:
        return {
            "action": action_match.group(1).lower(),  # Store the action as "buy" or "sell" (in lowercase)
            "symbol": symbol_match.group(1).upper()   # Symbol should be uppercase (e.g., BTC/USD)
        }
    return None

def get_existing_position(symbol):
    """Check if there is an existing position for the given symbol."""
    try:
        positions = ib.positions()
        for position in positions:
            if position.contract.symbol == symbol:
                logging.info(f"Existing position found for {symbol}: {position.position}")
                return position
        logging.info(f"No existing position for {symbol}.")
        return None
    except Exception as e:
        logging.error(f"Error fetching position for {symbol}: {e}")
        return None

def close_position(symbol):
    """Close the existing position for the given symbol."""
    position = get_existing_position(symbol)
    if position:
        logging.info(f"Closing existing position for {symbol}...")
        if position.position > 0:
            order = MarketOrder('SELL', position.position)
        elif position.position < 0:
            order = MarketOrder('BUY', abs(position.position))  # Buy to cover short position
        trade = ib.placeOrder(position.contract, order)
        trade.wait()  # Wait until the trade is completed
        logging.info(f"Position closed for {symbol}.")
        return trade
    else:
        logging.info(f"No position to close for {symbol}.")
        return None

def place_trade(symbol, action, qty=1):
    """Place a new trade using a dollar amount or share size."""
    try:
        contract = Stock(symbol, 'SMART', 'USD')
        if action == 'buy':
            order = MarketOrder('BUY', qty)  # Market buy order
        elif action == 'sell':
            order = MarketOrder('SELL', qty)  # Market sell order
        else:
            logging.error(f"Invalid action: {action}")
            return None
        trade = ib.placeOrder(contract, order)
        trade.wait()  # Wait until the trade is completed
        logging.info(f"Trade placed: {action} {qty} of {symbol}")
        return trade
    except Exception as e:
        logging.error(f"Error placing trade for {symbol}: {e}")
        return None

def process_trade(symbol, action):
    """Process a trade by closing the existing position (if any) and placing a new one."""
    logging.info(f"Processing trade for {symbol} - {action}")
    existing_position = get_existing_position(symbol)
    
    # Close any existing position
    if existing_position:
        logging.info(f"Existing position found for {symbol}. Closing it...")
        close_position(symbol)
    
    # Place the new trade (buy/sell)
    logging.info(f"Placing new {action} order for {symbol}...")
    return place_trade(symbol, action)

# Flask route to trigger email checking and trade placement
@app.route('/trigger', methods=['GET'])
def trigger_email_check():
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
        return jsonify({"message": "Email check complete", "trades": trades}), 200
    except Exception as e:
        logging.error(f"Error during trigger: {e}")
        return jsonify({"error": str(e)}), 500

# Flask route to check if the service is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Service is running"}), 200

# Background task to check for emails and place trades every 40 seconds
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
            time.sleep(25)  # Wait 40 seconds before checking again
        except Exception as e:
            logging.error(f"Error in background task: {e}")
            time.sleep(25)  # Wait before retrying if an error occurs

# Start the background task in a separate thread
@app.before_first_request
def start_background_task():
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()

if __name__ == "__main__":
    connect_ibkr()  # Connect to IBKR before running the app
    app.run(host='0.0.0.0', port=5000)


