from flask import Flask
import threading
import time
import logging
import sys

# Configure logging to force output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)  # Force output to Render's logs
    ]
)

app = Flask(__name__)

# Your bot functions here (simplified example)
def trading_bot():
    while True:
        try:
            logging.info("=== BOT ACTIVE ===")  # Test message
            # Add your actual bot logic here
            time.sleep(10)
        except Exception as e:
            logging.error(f"Bot error: {str(e)}")
            time.sleep(60)

# Start bot thread when Flask starts
@app.before_first_request
def start_bot():
    thread = threading.Thread(target=trading_bot, daemon=True)
    thread.start()
    logging.info(f"Bot thread started (Alive: {thread.is_alive()})")

@app.route('/')
def home():
    return "Trading Bot is running in background"

if __name__ == '__main__':
    start_bot()  # For local testing
    app.run(host='0.0.0.0', port=5000)
