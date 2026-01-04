import sys
import os
sys.path.append(os.getcwd())

from datetime import datetime, timedelta
from src.data.alpaca_market import AlpacaMarket
import pandas as pd

def test_history():
    print("Initializing AlpacaMarket...")
    try:
        market = AlpacaMarket()
    except Exception as e:
        print(f"Failed to init: {e}")
        return

    ticker = "NVDA"
    print(f"Fetching history for {ticker}...")
    
    try:
        # Test 1: Standard fetch
        df = market.get_history(ticker, days=10)
        
        if df is None:
            print("❌ Result is None")
        elif isinstance(df, pd.DataFrame):
            print(f"✅ Success! Got DataFrame with {len(df)} rows.")
            print(df.tail())
        else:
            print(f"❓ Got unexpected type: {type(df)}")
            print(df)

    except Exception as e:
        print(f"❌ Exception during fetch: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_history()
