from datetime import datetime, timedelta
from typing import Tuple

class RiskManager:
    def __init__(self, portfolio, market, logger):
        self.portfolio = portfolio
        self.market = market
        self.logger = logger
        self.min_notional = 5000.0
        self.max_notional = 25000.0
        self.max_position_pct = 0.20 # 20% max allocation per ticker
        self.last_trade_times = {} # {ticker: datetime}
        self.cooldown_minutes = 30

    def validate_order(self, ticker: str, action: str, shares: int) -> Tuple[bool, str]:
        """
        Validates if a proposed trade complies with risk rules.
        Returns (is_valid, rejection_reason).
        """
        try:
            current_price = self.market.get_price(ticker)
            if not current_price:
                return False, f"Could not fetch price for {ticker}"

            notional_value = shares * current_price
            portfolio_val = self.portfolio.get_total_value()
            cash = self.portfolio.get_cash()
            
            # 1. Size Constraints
            if notional_value < self.min_notional:
                return False, f"Notional ${notional_value:.2f} < Min ${self.min_notional}"
            
            if notional_value > self.max_notional:
                return False, f"Notional ${notional_value:.2f} > Max ${self.max_notional}"

            # 2. Logic Constraints
            if action == "BUY":
                # Cash check
                if notional_value > cash:
                    return False, f"Insufficient cash (${cash:.2f}) for trade (${notional_value:.2f})"
                
                # Exposure check (Post-trade value)
                current_shares = self.portfolio.get_positions().get(ticker, 0)
                new_total_value = (current_shares * current_price) + notional_value
                if new_total_value > (portfolio_val * self.max_position_pct):
                    return False, f"Exposure violation: New size would be > {self.max_position_pct*100}% of portfolio"

                # Cooldown check (Prevent wash-sale-like behavior / rapid re-entry)
                last_time = self.last_trade_times.get(ticker)
                if last_time:
                    elapsed = (datetime.now() - last_time).total_seconds() / 60
                    if elapsed < self.cooldown_minutes:
                        return False, f"Cooldown active: Last trade {int(elapsed)}m ago (Min {self.cooldown_minutes}m)"

            elif action == "SELL":
                # Ownership check
                owned_shares = self.portfolio.get_positions().get(ticker, 0)
                if shares > owned_shares:
                    return False, f"Cannot sell {shares} shares: only own {owned_shares}"

            # If all checks pass
            self.last_trade_times[ticker] = datetime.now()
            return True, "Trade Approved"

        except Exception as e:
            self.logger.error(f"Risk Validation Error: {e}")
            return False, f"Risk Validation Error: {e}"
