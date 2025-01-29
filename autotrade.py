import time
import re
import logging
from flask import Flask, jsonify
from ib_insync import IB, Stock, MarketOrder
import threading 

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app initialization
app = Flask(__name__)

# IBKR API credentials and settings
IBKR_HOST = '127.0.0.1'
IBKR_PORT = 7497  # Default for paper trading
IBKR_CLIENT_ID = 1  # Set an appropriate client ID

# Email credentials
EMAIL = "jtmendescb@gmail.com"
PASSWORD = "pkdj ptea aioo wqfy"
IMAP_SERVER = "imap.gmail.com"

# IBKR Connection Setup
ib = IB()

def connect_ibkr():
    """Connect to IBKR API (IB Gateway or TWS)."""
    try:
        ib.connect(IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID)
        logging.info("Connected to IBKR API")
    except Exception as e:
        logging.error(f"Error connecting to IBKR API: {e}")

def disconnect_ibkr():
    """Disconnect from IBKR API."""
    if ib.isConnected():
        ib.disconnect()
        logging.info("Disconnected from IBKR API")

# Function to connect to your email and fetch unread emails
def fetch_alert_emails():
    logging.info('Connecting to email server...')
    try:
        # Your existing email fetching logic here
        # For example, if using IMAP:
        # Assuming emails = some_imap_client.fetch_emails()
        emails = []  # If no emails found or an error occurs, return an empty list
        return emails
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []  # Return an empty list on error instead of None

def parse_email(content):
    """Parse email content to extract trading instructions."""
    logging.info(f"Parsing email content: {content}")
    action_match = re.search(r"Action[:\s]*([a-zA-Z]+)", content, re.IGNORECASE)
    symbol_match = re.search(r"Symbol[:\s]*([A-Za-z0-9]+)", content, re.IGNORECASE)

    if action_match:
        logging.info(f"Action found: {action_match.group(1)}")
    else:
        logging.warning("Action not found in the email.")

    if symbol_match:
        logging.info(f"Symbol found: {symbol_match.group(1)}")
    else:
        logging.warning("Symbol not found in the email.")

    if action_match and symbol_match:
        return {
            "action": action_match.group(1).lower(),
            "symbol": symbol_match.group(1).upper()
        }
    return None

def get_existing_position(symbol):
    """Check if there is an existing position for the given symbol."""
    try:
        positions = ib.positions()
        for position in positions:
            if position.contract.symbol == symbol:
                return position
        return None
    except Exception as e:
        logging.error(f"Error fetching position for {symbol}: {e}")
        return None

def close_position(symbol):
    """Close the existing position for the given symbol."""
    try:
        position = get_existing_position(symbol)
        if position:
            logging.info(f"Existing position found for {symbol}. Closing it...")
            
            if position.position > 0:
                # Long position: Sell to close
                order = MarketOrder('SELL', position.position)
            elif position.position < 0:
                # Short position: Buy to cover
                order = MarketOrder('BUY', abs(position.position))  # Buy to cover the short position

            trade = ib.placeOrder(position.contract, order)
            trade.wait()  # Wait until the trade is completed
            logging.info(f"Position closed for {symbol}.")
            return trade
        else:
            logging.info(f"No existing position for {symbol}. Nothing to close.")
            return None
    except Exception as e:
        logging.error(f"Error closing position for {symbol}: {e}")
        return None


def place_trade(symbol, action, notional=20):
    """Place a new trade using a dollar amount instead of quantity if the asset is not fractionable."""
    try:
        contract = Stock(symbol, 'SMART', 'USD')
        if action == 'buy':
            order = MarketOrder('BUY', notional)  # Market buy order
        elif action == 'sell':
            order = MarketOrder('SELL', notional)  # Market sell order
        else:
            logging.error(f"Invalid action: {action}")
            return None
        trade = ib.placeOrder(contract, order)
        trade.wait()  # Wait until the trade is completed
        logging.info(f"Trade placed: {action} {notional} of {symbol}")
        return trade
    except Exception as e:
        logging.error(f"Error placing trade for {symbol}: {e}")
        return None

def process_trade(symbol, action):
    """Process a trade by closing the existing position (if any) and placing a new one."""
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
                    result = process_trade(symbol, action)  # Process the trade (close old, place new)
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
            emails = fetch_alert_emails()  # Fetch the emails
            
            # Handle case if emails is None or empty list
            if not emails:
                logging.warning("No emails fetched or error in fetching emails.")
                emails = []  # Set to empty list if None or empty
            
            trades = []
            for email_content in emails:
                trade_data = parse_email(email_content)
                if trade_data:
                    action = trade_data["action"]
                    symbol = trade_data["symbol"]
                    if action in ['buy', 'sell']:
                        result = process_trade(symbol, action)  # Process the trade (close old, place new)
                        trades.append({"symbol": symbol, "action": action, "result": result})
            
            # Sleep before checking emails again
            time.sleep(25)
        
        except Exception as e:
            logging.error(f"Error in background task: {e}")
            time.sleep(25)  # Retry after 25 seconds if an error occurs

@app.route('/')
def home():
    return "Welcome to the trading API!"  # Or any message you want

# Start the background task in a separate thread
if __name__ == "__main__":
    connect_ibkr()  # Connect to IBKR API
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()  # Start background task in the background thread
    
    # Now run Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
