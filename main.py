from gevent import monkey
monkey.patch_all() 

from flask import Flask
import threading
import time
import logging
import sys
from email_reader import get_latest_alert, parse_alert
from alpaca_client import AlpacaTrader

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

class TradingBot:
    def __init__(self):
        self.trader = AlpacaTrader()
        self.last_processed = None
        self.active = True

    def run(self):
        logging.info("🚀 Bot Started")
        while self.active:
            try:
                self.check_alerts()
                time.sleep(10)
            except Exception as e:
                logging.error(f"Bot Error: {str(e)}", exc_info=True)
                time.sleep(60)

    def check_alerts(self):
        alert = get_latest_alert()
        if alert and alert != self.last_processed:
            direction = parse_alert(alert)
            if direction:
                logging.info(f"📶 New Signal: {direction.upper()}")
                if self.trader.execute_trade(direction):
                    self.last_processed = alert
                    logging.info("✅ Trade Executed")

# Initialize bot
bot = TradingBot()
bot_thread = threading.Thread(target=bot.run, daemon=True)
bot_thread.start()

@app.route('/')
def status():
    return {
        "status": "running",
        "bot_active": bot_thread.is_alive(),
        "last_processed": bool(bot.last_processed)
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
