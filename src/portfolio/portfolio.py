from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

class Portfolio:
    def __init__(self, start_cash: float = 100000.0):
        self.cash = start_cash
        self.positions: Dict[str, int] = {} # ticker -> shares
        self.history: List[Dict] = []
        self.start_cash = start_cash
        
        # Constraints
        self.MIN_TRADE_AMOUNT = 5000.0
        self.MAX_TRADE_AMOUNT = 25000.0

    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value (Cash + Holdings) based on current prices."""
        stock_value = 0.0
        for ticker, shares in self.positions.items():
            if ticker in current_prices and current_prices[ticker] is not None:
                stock_value += shares * current_prices[ticker]
            # If price missing, assume last known or handle error? 
            # For this sim, we might get price from MarketData individually.
        return self.cash + stock_value

    def validate_trade(self, ticker: str, action: str, shares: int, price: float) -> tuple[bool, str]:
        """
        Check if a proposed trade is valid under constraints.
        Action: "BUY" or "SELL"
        """
        amount = shares * price
        
        if amount <= 0:
            return False, "Trade amount must be positive."

        if action.upper() == "BUY":
            if amount > self.cash:
                return False, f"Insufficient cash. Have ${self.cash:.2f}, need ${amount:.2f}."
            if amount < self.MIN_TRADE_AMOUNT:
                return False, f"Trade amount ${amount:.2f} below minimum ${self.MIN_TRADE_AMOUNT}."
            if amount > self.MAX_TRADE_AMOUNT:
                return False, f"Trade amount ${amount:.2f} exceeds maximum ${self.MAX_TRADE_AMOUNT}."
            
        elif action.upper() == "SELL":
            current_shares = self.positions.get(ticker, 0)
            if shares > current_shares:
                return False, f"Insufficient shares. Have {current_shares}, need {shares}."
                
            # Note: We don't strictly enforce min/max on SELL in the prompt description, but usually max limit applies to opening positions.
            # We will allow selling small amounts if it closes a position, or large amounts.
            # But "position size" constraints usually apply to *holding* size or *entry* size.
            # Let's enforce min sell unless it's the entire position.
            
            is_full_exit = (shares == current_shares)
            if not is_full_exit and amount < self.MIN_TRADE_AMOUNT:
                 return False, f"Sell amount ${amount:.2f} below minimum ${self.MIN_TRADE_AMOUNT} (unless full exit)."

        else:
            return False, f"Unknown action {action}"

        return True, "Valid"

    def execute_trade(self, ticker: str, action: str, shares: int, price: float, date: datetime):
        """Execute the trade, updating cash and positions."""
        is_valid, reason = self.validate_trade(ticker, action, shares, price)
        if not is_valid:
            print(f"Trade Rejected [{date.date()}]: {action} {shares} {ticker} @ ${price:.2f} -> {reason}")
            return False

        amount = shares * price
        if action.upper() == "BUY":
            self.cash -= amount
            self.positions[ticker] = self.positions.get(ticker, 0) + shares
        elif action.upper() == "SELL":
            self.cash += amount
            self.positions[ticker] -= shares
            if self.positions[ticker] == 0:
                del self.positions[ticker]
        
        # Log trade
        self.history.append({
            "date": date,
            "ticker": ticker,
            "action": action,
            "shares": shares,
            "price": price,
            "amount": amount,
            "cash_after": self.cash
        })
        print(f"Trade Executed [{date.date()}]: {action} {shares} {ticker} @ ${price:.2f}")
        return True

    def get_holdings_summary(self) -> str:
        if not self.positions:
            return "Cash only."
        items = [f"{t}: {s} shares" for t, s in self.positions.items()]
        return ", ".join(items)
