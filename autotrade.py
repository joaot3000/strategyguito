import logging
import re
import os
from imapclient import IMAPClient
import email
from email.policy import default
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask, jsonify
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import time
from ib_insync import *

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

# Initialize IBKR client
ib = IB()

# Function to send Telegram messages
async def send_telegram_message(message):
    try:
        await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
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
                # Close existing position if necessary
                close_position(symbol, action)
                # Place the new trade
                result = place_trade(symbol, action)
                logging.info(f"Trade result: {result}")
                # Send Telegram message
                send_telegram_message(f"Trade executed: {action} {symbol}, Result: {result}")
    else:
        logging.info("No new emails found.")

# Now, set the scheduler to run the check_emails_periodically() every 10 seconds
scheduler = BackgroundScheduler()
scheduler.add_job(check_emails_periodically, 'interval', seconds=10)  # Run every 10 seconds
scheduler.start()

def get_open_position(symbol):
    """
    Fetch all positions and return the one for the given symbol.
    Returns None if no position is found for the symbol.
    """
    positions = ib.positions()
    for position in positions:
        if position.contract.symbol == symbol:
            return {
                'symbol': position.contract.symbol,
                'qty': position.position,
                'side': 'long' if position.position > 0 else 'short',
            }
    return None

def get_available_balance(symbol):
    """
    Get the available balance for a given symbol.
    """
    account_values = ib.accountValues()
    for value in account_values:
        if value.tag == 'AvailableFunds' and value.currency == 'USD':
            return float(value.value)
    return None

def close_position(symbol, action):
    """
    Close the open position for the given symbol.
    """
    current_position = get_open_position(symbol)

    if action == "sell":
        if current_position and current_position['side'] == 'long':
            logging.info(f"Received sell signal for {symbol}. Closing long position.")
            close_trade(symbol, 'sell', abs(float(current_position['qty'])))
        elif not current_position:
            logging.info(f"No open position for {symbol}. Proceeding with sell.")
        else:
            logging.info(f"Proceeding with sell for {symbol}, no open long position.")

    elif action == "buy":
        if current_position and current_position['side'] == 'short':
            logging.info(f"Received buy signal for {symbol}. Closing short position.")
            close_trade(symbol, 'buy', abs(float(current_position['qty'])))
        elif not current_position:
            logging.info(f"No open position for {symbol}. Proceeding with buy.")
        else:
            logging.info(f"Proceeding with buy for {symbol}, no open short position.")
    
    else:
        logging.error(f"Invalid action: {action}. Expected 'sell' or 'buy'.")

def place_trade(symbol, side, qty=0.008):
    """
    Place a market order for the given symbol and side (buy/sell).
    """
    available_balance = get_available_balance(symbol)
    
    if available_balance is None:
        logging.error(f"Unable to fetch available balance for {symbol}.")
        return None
    
    if qty > available_balance:
        logging.warning(f"Requested quantity {qty} exceeds available balance {available_balance}. Adjusting trade size.")
        qty = available_balance  # Adjust the trade size to the available balance

    contract = Stock(symbol, 'SMART', 'USD')
    order = MarketOrder(side.upper(), qty)
    trade = ib.placeOrder(contract, order)
    ib.sleep(1)  # Wait for the order to be filled

    if trade.orderStatus.status == 'Filled':
        logging.info(f"Order placed successfully: {trade}")
        return trade
    else:
        logging.error(f"Failed to place order. Status: {trade.orderStatus.status}")
        return None

def close_trade(symbol, side, qty):
    """
    Close a trade (buy or sell) for a symbol with the specified quantity.
    """
    return place_trade(symbol, side, qty)

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
                    current_position = get_open_position(symbol)
                    if current_position and current_position['side'] != action:
                        logging.info(f"Closing the existing position for {symbol} before placing the {action} trade.")
                        close_position(symbol, action)
                    result = place_trade(symbol, action)
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

        current_position = get_open_position(symbol)
        if current_position and current_position['side'] != side:
            await update.message.reply_text(f"Closing the existing position for {symbol} before placing the {side} trade.")
            close_position(symbol, side)

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
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

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

    # Connect to IBKR
    ib.connect('127.0.0.1', 7497, clientId=1)  # Adjust host and port as needed

    # Start polling for Telegram Bot
    application.run_polling()

if __name__ == "__main__":
    main()
