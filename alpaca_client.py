from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import logging
from config import Config

class AlpacaTrader:
    def __init__(self):
        self.client = TradingClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            paper=Config.PAPER_TRADING
        )
        self.symbol = Config.TRADE_SYMBOL
        self.quantity = Config.TRADE_QUANTITY

    def execute_trade(self, direction):
        try:
            # Validate direction
            if direction.lower() not in ['buy', 'sell']:
                raise ValueError(f"Invalid direction: {direction}")
            
            # Create order request
            order_data = MarketOrderRequest(
                symbol=self.symbol,
                notional=self.quantity,  # Use notional for fractional shares
                side=OrderSide.BUY if direction.lower() == 'buy' else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            
            # Execute trade
            order = self.client.submit_order(order_data)
            logging.info(
                f"Executed {direction.upper()} order for {self.quantity} shares of {self.symbol} "
                f"(Order ID: {order.id})"
            )
            return True
            
        except Exception as e:
            logging.error(f"Trade failed: {str(e)}")
            return False
