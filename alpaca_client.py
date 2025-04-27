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
            paper=True
        )

    def execute_trade(self, direction):
        try:
            order_data = MarketOrderRequest(
                symbol="SPY",
                qty=1,
                side=OrderSide.BUY if direction == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            order = self.client.submit_order(order_data)
            logging.info(f"Order submitted: {order.id}")
            return True
        except Exception as e:
            logging.error(f"Trade Error: {str(e)}")
            return False
