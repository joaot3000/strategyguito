import time
import re
import requests
from imapclient import IMAPClient
import email
from email.policy import default
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Alpaca API credentials
ALPACA_API_URL = "https://paper-api.alpaca.markets/v2"
ALPACA_API_KEY = "PKCCAHDTUSPTYNMRQBA2"
ALPACA_SECRET_KEY = "Peh8XoPBwmgrxxfPvGKO5F8SnfHZt6lVsybUJ8qy"

# Email credentials
EMAIL = "jtmendescb@gmail.com"
PASSWORD = "pkdj ptea aioo wqfy"
IMAP_SERVER = "imap.gmail.com"  # e.g., imap.gmail.com

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

def place_trade(symbol, side, qty=0.014):
    endpoint = f"https://paper-api.alpaca.markets/v2/orders"
    headers = {
        "APCA-API-KEY-ID": "PKCCAHDTUSPTYNMRQBA2",
        "APCA-API-SECRET-KEY": "Peh8XoPBwmgrxxfPvGKO5F8SnfHZt6lVsybUJ8qy"
    }

    # Ensure the side is either "buy" or "sell"
    if side.lower() not in ["buy", "sell"]:
        print(f"Invalid side: {side}")
        return None

    order = {
        "symbol": symbol,
        "qty": qty,
        "side": side,  # Ensure it's in lowercase
        "type": "market",
        "time_in_force": "gtc"
    }

    try:
        # Send the POST request to place the order
        response = requests.post(endpoint, json=order, headers=headers)

        # Check the HTTP status code
        if response.status_code == 200:
            print(f"Success! Status code: {response.status_code}")
            try:
                # Try to parse the JSON response
                return response.json()  # This should work if the response is valid JSON
            except ValueError:
                print(f"Error: Unable to decode JSON from response. Response text: {response.text}")
                return None
        else:
            # Handle non-200 status codes
            print(f"Error: Received non-200 status code {response.status_code}. Response text: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        # This catches any exceptions such as network errors, timeouts, etc.
        print(f"Error during request: {e}")
        return None

# Main function to monitor email and place trades
def main():
    while True:
        try:
            emails = fetch_alert_emails()
            logging.info(f'Fetched {len(emails)} emails for processing.')
        except Exception as e:
            logging.error(f'Error fetching emails: {e}')
            time.sleep(5)  # Wait before retrying in case of an error
            continue
            
        for email_content in emails:
            trade_data = parse_email(email_content)
            if trade_data:
                action = trade_data["action"]
                symbol = trade_data["symbol"]
                
                if action in ['buy', 'sell']:
                    print(f"Placing {action.upper()} order for {symbol}")
                    result = place_trade(symbol, action)  # "buy" or "sell" will be passed here
                    print(f"Trade result: {result}")
        time.sleep(5)

if __name__ == "__main__":
    main()