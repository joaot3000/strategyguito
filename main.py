from flask import Flask
import threading
import time
import logging
import sys

app = Flask(__name__)

# Force all logs to Render's output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def trading_bot():
    while True:
        try:
            logging.info("=== BOT ACTIVE ===")
            # Your actual bot logic here
            time.sleep(10)
        except Exception as e:
            logging.error(f"Bot error: {str(e)}")
            time.sleep(60)

# Start bot thread when app starts
with app.app_context():
    bot_thread = threading.Thread(target=trading_bot, daemon=True)
    bot_thread.start()
    logging.info(f"Bot thread started (Alive: {bot_thread.is_alive()})")

@app.route('/')
def home():
    return "Trading Bot is running in background"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
