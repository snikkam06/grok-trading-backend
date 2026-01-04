import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators for a given DataFrame of OHLCV data.
    Expected columns: 'close', 'high', 'low'
    Uses pure pandas to avoid dependency issues.
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    close = df['close']
    
    # 1. Simple Moving Averages
    df['SMA_20'] = close.rolling(window=20).mean()
    df['SMA_50'] = close.rolling(window=50).mean()
    df['SMA_200'] = close.rolling(window=200).mean()
    
    # 2. RSI (Relative Strength Index) - 14 period
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # 3. ATR (Average True Range) - 14 period
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - close.shift())
    low_close = np.abs(df['low'] - close.shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    df['ATR_14'] = true_range.rolling(window=14).mean()

    return df

def get_latest_indicators(df: pd.DataFrame) -> dict:
    """
    Return the latest indicator values as a dictionary.
    """
    if df is None or df.empty:
        return {}
        
    latest = df.iloc[-1]
    
    # Helper to safe get
    def get_val(key):
        val = latest.get(key, 0)
        return val if not pd.isna(val) else 0

    price = get_val('close')
    sma_50 = get_val('SMA_50')
    
    return {
        "price": price,
        "rsi": round(get_val('RSI_14'), 2),
        "sma_50": round(sma_50, 2),
        "sma_200": round(get_val('SMA_200'), 2),
        "atr": round(get_val('ATR_14'), 2),
        "trend": "Bullish" if price > sma_50 else "Bearish"
    }
