import alpaca_trade_api as tradeapi
from config import Config
import logging

class AlpacaTrader:
    def __init__(self):
        self.api = tradeapi.REST(
            Config.APCA_API_KEY_ID,
            Config.APCA_API_SECRET_KEY,
            base_url=Config.APCA_BASE_URL
        )
    
    def _close_position(self):
        try:
            position = self.api.get_position(Config.SYMBOL)
            self.api.submit_order(
                symbol=Config.SYMBOL,
                qty=abs(float(position.qty)),
                side='sell' if float(position.qty) > 0 else 'buy',
                type='market',
                time_in_force='gtc'
            )
            logging.info(f"Closed {position.qty} shares of {Config.SYMBOL}")
            return True
        except Exception as e:
            if "404" in str(e):  # No position exists
                return True
            logging.error(f"Position close failed: {e}")
            return False
    
    def execute_trade(self, direction):
        if not self._close_position():
            return False
        
        try:
            self.api.submit_order(
                symbol=Config.SYMBOL,
                qty=Config.QTY,
                side='buy' if direction == 'long' else 'sell',
                type='market',
                time_in_force='gtc'
            )
            logging.info(f"Opened {direction} position: {Config.QTY} {Config.SYMBOL}")
            return True
        except Exception as e:
            logging.error(f"Trade execution failed: {e}")
            return False
