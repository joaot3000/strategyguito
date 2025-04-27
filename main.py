from flask import Flask
import threading
import logging
import time

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def dummy_bot():
    while True:
        logging.info("=== BOT IS ALIVE ===")
        time.sleep(5)

@app.route('/')
def home():
    return "Test running"

if __name__ == '__main__':
    # Start thread with explicit logging
    threading.Thread(target=dummy_bot, daemon=True).start()
    logging.info("Main thread started")
    app.run(host='0.0.0.0', port=5000)
