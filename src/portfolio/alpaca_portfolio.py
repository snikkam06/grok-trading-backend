import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from dotenv import load_dotenv

load_dotenv()

class AlpacaPortfolio:
    def __init__(self):
        api_key = os.getenv('APCA_API_KEY_ID')
        secret_key = os.getenv('APCA_API_SECRET_KEY')
        base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        
        if not api_key or not secret_key:
            raise ValueError("Alpaca API keys (APCA_API_KEY_ID, APCA_API_SECRET_KEY) must be set in .env")
            
        self.client = TradingClient(api_key, secret_key, paper=True)

    def get_total_value(self) -> float:
        account = self.client.get_account()
        return float(account.portfolio_value)

    def get_cash(self) -> float:
        account = self.client.get_account()
        return float(account.cash)

    def get_positions(self) -> dict:
        positions = self.client.get_all_positions()
        return {p.symbol: int(p.qty) for p in positions}

    def get_holdings_summary(self) -> str:
        pos = self.get_positions()
        if not pos:
            return "Cash only."
        return ", ".join([f"{symbol}: {qty} shares" for symbol, qty in pos.items()])

    def execute_trade(self, ticker: str, action: str, shares: int):
        """Execute a market order on Alpaca."""
        side = OrderSide.BUY if action.upper() == "BUY" else OrderSide.SELL
        
        print(f"Submitting {action} order for {shares} shares of {ticker} to Alpaca...")
        
        order_details = MarketOrderRequest(
            symbol=ticker,
            qty=shares,
            side=side,
            time_in_force=TimeInForce.GTC
        )
        
        try:
            order = self.client.submit_order(order_data=order_details)
            print(f"Order submitted: {order.id}")
            return True
        except Exception as e:
            print(f"Error submitting order to Alpaca: {e}")
            return False
