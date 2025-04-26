from email_reader import get_latest_alert, parse_alert
from alpaca_client import AlpacaTrader
import time
import logging

# Initialize
trader = AlpacaTrader()
last_processed = None

# Logging
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

if __name__ == "__main__":
    logging.info("Alpaca TradingView Bot Started")
    while True:
        process_alerts()
        time.sleep(10)  # Check every minute
