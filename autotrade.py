import logging
import re
import requests
from imapclient import IMAPClient
import email
from email.policy import default
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask, jsonify
import os
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import time

# Set up logging configuration to show detailed debug information
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask app initialization
app = Flask(__name__)

# Binance Testnet API credentials
BINANCE_API_URL = "https://testnet.binance.vision/api/v3"
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "your_api_key_here")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "your_secret_key_here")

# Email credentials
EMAIL = os.getenv("EMAIL", "jtmendescb@gmail.com")
PASSWORD = os.getenv("EMAIL_PASSWORD", "pkdj ptea aioo wqfy")
IMAP_SERVER = "imap.gmail.com"  # e.g., imap.gmail.com

# Telegram Bot credentials
Bot = os.getenv("Bot", "7897853987:AAEVLNuZxCWT8CmzqszUf9sJ5PdLfNq4vLg")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5825643489")

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
                # Here, you could add logic to check positions and place trades
                # For example, you could call your Binance trading functions here.
                result = place_trade(symbol, action)
                logging.info(f"Trade result: {result}")
    else:
        logging.info("No new emails found.")

# Now, set the scheduler to run the check_emails_periodically() every 10 seconds
scheduler = BackgroundScheduler()
scheduler.add_job(check_emails_periodically, 'interval', seconds=10)  # Run every 10 seconds
scheduler.start()

# Function to get the available balance for a given symbol
def get_available_balance(symbol):
    endpoint = f"{BINANCE_API_URL}/account"
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }

    params = {
        'timestamp': int(time.time() * 1000),
        'signature': generate_signature(params)
    }
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        if response.status_code == 200:
            account_info = response.json()

            balance = None
            for asset in account_info['balances']:
                if asset['asset'] == symbol:
                    balance = float(asset['free'])  # Free balance available for trading
                    logging.info(f"Available balance for {symbol}: {balance}")
                    break

            return balance if balance else 0
        else:
            logging.error(f"Failed to fetch balance. Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during request: {e}")
        return None

# Function to close an open position (Binance doesn't directly support this like Alpaca, so we'll cancel orders)
def close_position(symbol):
    endpoint = f"{BINANCE_API_URL}/openOrders"
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }

    params = {
        'symbol': symbol,
        'timestamp': int(time.time() * 1000),
        'signature': generate_signature(params)
    }

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        if response.status_code == 200:
            open_orders = response.json()
            for order in open_orders:
                # Cancel open orders (if any)
                cancel_order(symbol, order['orderId'])
        else:
            logging.error(f"Failed to fetch open orders. Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during request: {e}")

# Function to cancel an order
def cancel_order(symbol, order_id):
    endpoint = f"{BINANCE_API_URL}/order"
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }

    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': int(time.time() * 1000),
        'signature': generate_signature(params)
    }

    try:
        response = requests.delete(endpoint, headers=headers, params=params)
        if response.status_code == 200:
            logging.info(f"Order {order_id} for {symbol} cancelled successfully.")
        else:
            logging.error(f"Failed to cancel order. Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during request: {e}")

# Generate signature for Binance API
def generate_signature(params):
    query_string = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
    return hmac.new(BINANCE_SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# Function to place a trade (buy/sell) using Binance API
def place_trade(symbol, side, qty=0.008):
    available_balance = get_available_balance(symbol)

    if available_balance is None:
        logging.error(f"Unable to fetch available balance for {symbol}.")
        return None
    
    # Check if the requested quantity is more than the available balance
    if qty > available_balance:
        logging.warning(f"Requested quantity {qty} exceeds available balance {available_balance}. Adjusting trade size.")
        qty = available_balance  # Adjust the trade size to the available balance

    # Create order data for Binance
    order = {
        "symbol": symbol,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": qty,
        'timestamp': int(time.time() * 1000),
        'signature': generate_signature(order)
    }

    try:
        endpoint = f"{BINANCE_API_URL}/order"
        headers = {
            "X-MBX-APIKEY": BINANCE_API_KEY
        }

        response = requests.post(endpoint, json=order, headers=headers)

        if response.status_code == 200:
            trade_result = response.json()
            logging.info(f"Order placed successfully: {trade_result}")
            send_telegram_message(f"Trade executed: {side.upper()} {qty} of {symbol}")
            return trade_result
        else:
            logging.error(f"Failed to place order. Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during request: {e}")
        return None

def send_telegram_message(message):
    """Send a notification to Telegram."""
    url = f"https://api.telegram.org/bot{Bot}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info("Telegram notification sent successfully.")
        else:
            logging.error(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")


# Flask route to trigger email checking and trade placement
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
        if trades:
            return jsonify({"message": "Trade(s) executed", "trades": trades}), 200
        else:
            logging.info("No valid trades found in emails.")
            return jsonify({"message": "Email check complete, no trades found", "trades": []}), 200
    except Exception as e:
        logging.error(f"Error during trigger: {e}")
        return jsonify({"error": str(e)}), 500

# Flask route to check if the service is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Service is running"}), 200

# Telegram Bot Setup
async def start(update: Update, context: CallbackContext) -> None:
    """Start command.""" 
    await update.message.reply_text("Welcome to the Trading Bot!")

async def check_email(update: Update, context: CallbackContext) -> None:
    """Fetch email trade signals.""" 
    emails = fetch_alert_emails() 
    if emails: 
        await update.message.reply_text(f"Found {len(emails)} new email(s).")
    else:
        await update.message.reply_text("No new emails found.")

async def trade(update: Update, context: CallbackContext) -> None:
    """Place a trade via Telegram command.""" 
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("Usage: /trade <symbol> <qty> <buy/sell>")
            return

        symbol, qty, side = args[0], float(args[1]), args[2].lower()
        if side not in ["buy", "sell"]:
            await update.message.reply_text("Trade side must be 'buy' or 'sell'.")
            return

        result = place_trade(symbol, side, qty)
        if result:
            await update.message.reply_text(f"Trade executed: {result}")
        else:
            await update.message.reply_text("Failed to execute trade.")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Run the Telegram Bot with Flask
def main():
    """Run the bot.""" 
    application = Application.builder().token(Bot).build()

    # Add command handlers 
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check_email", check_email))
    application.add_handler(CommandHandler("trade", trade))

    # Start Flask app in background 
    def run_flask():
        app.run(host='0.0.0.0', port=5000)

    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True  # Daemonize thread
    flask_thread.start()

    # Start polling for Telegram Bot
    application.run_polling()

if __name__ == "__main__":
    main()
