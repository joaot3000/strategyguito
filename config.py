import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Alpaca API
    APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID")
    APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
    APCA_BASE_URL = os.getenv("APCA_BASE_URL", "https://paper-api.alpaca.markets")
    
    # Email
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    # Trading
    SYMBOL = os.getenv("SYMBOL", "SPY")
    QTY = int(os.getenv("QTY", 3))
