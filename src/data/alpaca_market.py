import os
from alpaca.trading.client import TradingClient
from typing import Any
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from dotenv import load_dotenv

load_dotenv()

class AlpacaMarket:
    def __init__(self):
        api_key = os.getenv('APCA_API_KEY_ID')
        secret_key = os.getenv('APCA_API_SECRET_KEY')
        
        if not api_key or not secret_key:
            raise ValueError("Alpaca API keys (APCA_API_KEY_ID, APCA_API_SECRET_KEY) must be set in .env")
            
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.trading_client = TradingClient(api_key, secret_key, paper=True)

    def get_price(self, ticker: str) -> float:
        """Get the latest quote price for a ticker."""
        try:
            request_params = StockLatestQuoteRequest(symbol_or_symbols=ticker)
            quote = self.data_client.get_stock_latest_quote(request_params)
            # Alpaca returns a dict of quotes
            return float(quote[ticker].ask_price) # Use ask price for simulation
        except Exception as e:
            print(f"Error fetching price for {ticker} from Alpaca: {e}")
            return None

    def is_market_open(self) -> bool:
        """Check if the market is currently open."""
        clock = self.trading_client.get_clock()
        return clock.is_open

    def get_history(self, ticker: str, days: int = 100, timeframe: str = 'Day') -> Any:
        """
        Get historical data for a ticker.
        
        Args:
            ticker: Symbol name (e.g. 'AAPL')
            days: Number of days of history to fetch
            timeframe: 'Day', 'Hour', or 'Minute'
            
        Returns:
            DataFrame with history or None
        """
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from datetime import datetime, timedelta

        try:
            # Map string to Alpaca TimeFrame
            tf_map = {
                'Day': TimeFrame.Day,
                'Hour': TimeFrame.Hour,
                'Minute': TimeFrame.Minute
            }
            tf = tf_map.get(timeframe, TimeFrame.Day)
            
            # logical approx for start time
            # For daily, we want N trading days. We ask for N*1.5 calendar days roughly.
            start_dt = datetime.now() - timedelta(days=int(days*1.5))
            
            req = StockBarsRequest(
                symbol_or_symbols=ticker,
                timeframe=tf,
                start=start_dt
            )
            
            bars = self.data_client.get_stock_bars(req)
            
            if bars.data:
                df = bars.df
                # Handle MultiIndex (symbol, timestamp)
                if ticker in df.index.levels[0]: 
                    return df.xs(ticker, level=0)
                # Fallback implementation if structure differs
                return df
            
            return None
        except Exception as e:
            print(f"Error fetching history for {ticker}: {e}")
            return None

    def get_snapshots(self, tickers: list) -> dict:
        """
        Get daily snapshots (price, change, volume) for a list of tickers.
        """
        try:
            from alpaca.data.requests import StockSnapshotRequest
            
            # Alpaca lets you request snapshots for multiple symbols
            req = StockSnapshotRequest(symbol_or_symbols=tickers)
            snapshots = self.data_client.get_stock_snapshot(req)
            
            results = {}
            for ticker, snap in snapshots.items():
                if snap:
                    results[ticker] = {
                        "price": snap.latest_trade.price,
                        "change_pct": (snap.daily_bar.close - snap.daily_bar.open) / snap.daily_bar.open * 100 if snap.daily_bar else 0.0,
                        "volume": snap.daily_bar.volume if snap.daily_bar else 0
                    }
            return results
        except Exception as e:
            print(f"Error fetching snapshots: {e}")
            return {}
