import os
from dotenv import load_dotenv

class Config:
    # Load environment variables
    load_dotenv()
    
    # Email Configuration
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    
    # Trading Configuration
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
    
    # Trade Execution Parameters
    TRADE_SYMBOL = os.getenv('TRADE_SYMBOL', 'SPY')          # Default to SPY
    TRADE_QUANTITY = float(os.getenv('TRADE_QUANTITY', 1))   # Default to 1 share
    MAX_TRADE_SIZE = float(os.getenv('MAX_TRADE_SIZE', 10000)) # Dollar limit
    
    # Validation
    @classmethod
    def validate(cls):
        required = [
            'EMAIL_ADDRESS', 'EMAIL_PASSWORD',
            'ALPACA_API_KEY', 'ALPACA_SECRET_KEY'
        ]
        missing = [var for var in required if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing config: {', '.join(missing)}")
        
        if cls.TRADE_QUANTITY <= 0:
            raise ValueError("TRADE_QUANTITY must be positive")

Config.validate()
