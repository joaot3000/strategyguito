from flask import Flask
import threading
import time
from email_reader import get_latest_alert, parse_alert
from alpaca_client import AlpacaTrader
import logging

app = Flask(__name__)

# Initialize trading bot components
trader = AlpacaTrader()
last_processed = None

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

def process_alerts():
    global last_processed
    email_body = get_latest_alert()
    if email_body != last_processed:
        direction = parse_alert(email_body)
        if direction:
            logging.info(f"New signal: {direction.upper()}")
            if trader.execute_trade(direction):
                last_processed = email_body

# Run bot in background thread
def run_bot():
    logging.info("Bot started in background thread")
    while True:
        try:
            process_alerts()
            time.sleep(10)
        except Exception as e:
            logging.error(f"Bot error: {e}")

# Start thread when Flask initializes
threading.Thread(target=run_bot, daemon=True).start()

@app.route('/')
def home():
    return "Trading Bot Active | Check logs for trade signals"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
