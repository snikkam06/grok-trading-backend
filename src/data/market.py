import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

class MarketData:
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
        self.cache = {}  # Cache for ticker data to avoid redundant API calls
        self.current_sim_date = start_date # The "Now" in the simulation

    def set_simulation_date(self, date: datetime):
        """Update the current simulation date. This controls what data is visible."""
        # Ensure we don't go backwards or jump weirdly if strictness is needed, 
        # but for now just setting it is fine.
        self.current_sim_date = date

    def get_price(self, ticker: str) -> float:
        """Get the closing price of the ticker on the current simulation date."""
        df = self._get_ticker_data(ticker)
        
        # We look for the row corresponding to self.current_sim_date
        # If exact date missing (weekend/holiday), get the last available close before or on that date.
        
        mask = df.index <= pd.Timestamp(self.current_sim_date)
        df_filtered = df[mask]
        
        if df_filtered.empty:
            return None # No data available yet for this date (maybe listing date is later)
        
        latest_row = df_filtered.iloc[-1]
        return float(latest_row['Close'])

    def get_history(self, ticker: str, days: int = 30) -> str:
        """
        Get a string summary of price history up to current simulation date.
        Useful for providing context to the LLM.
        """
        df = self._get_ticker_data(ticker)
        mask = df.index <= pd.Timestamp(self.current_sim_date)
        df_filtered = df[mask].tail(days)
        
        if df_filtered.empty:
            return "No history available."
            
        # Format as string
        # Date: Close Price (Volume)
        lines = []
        for date, row in df_filtered.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            close = f"{row['Close']:.2f}"
            lines.append(f"{date_str}: ${close}")
            
        return "\n".join(lines)

    def _get_ticker_data(self, ticker: str) -> pd.DataFrame:
        """Internal helper to fetch and cache full history for the ticker."""
        if ticker in self.cache:
            return self.cache[ticker]
        
        # We download slightly more than needed to be safe, or just max
        # It's better to fetch everything once and filter in memory since backtest is offline-ish.
        print(f"Fetching data for {ticker}...")
        try:
            # We can download from a safe start year like 2023 to capture enough history
            df = yf.download(ticker, start="2023-01-01", end=self.end_date + timedelta(days=1), progress=False)
            if df.empty:
                print(f"Warning: No data found for {ticker} (yfinance failed). Using Synthetic Data.")
                return self._generate_synthetic_data(ticker)
            self.cache[ticker] = df
            return df
        except Exception as e:
            print(f"Error fetching {ticker}: {e}. Using Synthetic Data.")
            return self._generate_synthetic_data(ticker)

    def _generate_synthetic_data(self, ticker: str) -> pd.DataFrame:
        """Generate fake price history for testing when API fails."""
        dates = pd.date_range(start=self.start_date - timedelta(days=365), end=self.end_date)
        import numpy as np
        
        # simple random walk
        np.random.seed(sum(ord(c) for c in ticker)) 
        start_price = 150.0
        returns = np.random.normal(0.0005, 0.02, len(dates))
        prices = start_price * np.cumprod(1 + returns)
        
        df = pd.DataFrame(index=dates)
        df['Close'] = prices
        df['Open'] = prices # simplify
        df['High'] = prices
        df['Low'] = prices
        df['Volume'] = 1000000
        self.cache[ticker] = df
        return df

# Simple Test
if __name__ == "__main__":
    mk = MarketData(datetime(2025, 2, 1), datetime(2025, 10, 1))
    mk.set_simulation_date(datetime(2025, 3, 1))
    print("Price of AAPL on March 1, 2025:", mk.get_price("AAPL"))
    print("\nHistory of AAPL (last 5 days):")
    print(mk.get_history("AAPL", 5))
