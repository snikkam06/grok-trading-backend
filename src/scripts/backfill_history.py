import os
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Raw data provided by user
TRADES_DATA = """
NVDA	buy	133.00	187.231579	Dec 31, 2025, 02:51:09 PM
WDC	sell	356.00	172.15	Dec 31, 2025, 02:51:07 PM
WDC	buy	356.00	172.30	Dec 31, 2025, 02:40:36 PM
NVDA	sell	133.00	187.254662	Dec 31, 2025, 02:40:37 PM
NVDA	buy	128.00	187.148125	Dec 31, 2025, 02:29:59 PM
NVDA	buy	133.00	187.148572	Dec 31, 2025, 02:29:59 PM
ASTS	sell	333.00	71.93	Dec 31, 2025, 02:30:00 PM
ASTS	sell	346.00	71.93	Dec 31, 2025, 02:29:57 PM
NVDA	buy	97.00	187.608041	Dec 31, 2025, 02:19:16 PM
DYN	sell	900.00	19.51	Dec 31, 2025, 02:19:17 PM
DYN	buy	900.00	19.53	Dec 31, 2025, 02:08:49 PM
NVDA	sell	100.00	187.52	Dec 31, 2025, 02:08:49 PM
NVDA	buy	133.00	187.80	Dec 31, 2025, 01:58:18 PM
ASTS	sell	330.00	72.21	Dec 31, 2025, 01:58:18 PM
ASTS	buy	344.00	72.59	Dec 31, 2025, 01:47:41 PM
NVDA	sell	133.00	187.69	Dec 31, 2025, 01:47:41 PM
ASTS	buy	338.00	73.45	Dec 31, 2025, 01:16:11 PM
NVDA	sell	132.00	188.51	Dec 31, 2025, 01:16:12 PM
NVDA	buy	132.00	188.720909	Dec 31, 2025, 01:05:37 PM
ASTS	sell	338.00	73.81	Dec 31, 2025, 01:05:36 PM
ASTS	buy	327.00	74.01	Dec 31, 2025, 12:54:59 PM
QBTS	sell	900.00	26.71	Dec 31, 2025, 12:55:01 PM
QBTS	buy	900.00	26.88	Dec 31, 2025, 12:44:29 PM
VNDA	sell	2782.00	9.01	Dec 31, 2025, 12:44:30 PM
NVDA	buy	132.00	188.83	Dec 31, 2025, 12:33:52 PM
VNDA	sell	2756.00	9.04	Dec 31, 2025, 12:33:52 PM
ASTS	buy	338.00	73.82	Dec 31, 2025, 12:23:13 PM
VNDA	buy	2774.00	9.01	Dec 31, 2025, 12:23:13 PM
RZLV	sell	9534.00	2.59	Dec 31, 2025, 12:23:13 PM
AUR	sell	6510.00	3.83	Dec 31, 2025, 12:23:12 PM
NVDA	buy	132.00	188.88	Dec 31, 2025, 12:12:38 PM
AUR	buy	6510.00	3.84	Dec 31, 2025, 12:12:38 PM
RZLV	buy	9534.00	2.62	Dec 31, 2025, 12:12:37 PM
VNDA	buy	2764.00	9.03	Dec 31, 2025, 12:12:38 PM
"""

REASONING_MAP = {
    "NVDA": {
        "buy": "Scaling into momentum position. Strong AI demand tailwinds.",
        "sell": "Profit taking on core position. Rebalancing portfolio risk."
    },
    "ASTS": {
        "buy": "Accumulating on satellite launch optimism and oversold RSI.",
        "sell": "Exiting satellite position due to short-term momentum shift."
    },
    "VNDA": {
        "buy": "Value play on biotech pipeline. Low price-to-book entry.",
        "sell": "Closing biotech position to free up capital for high-conviction tech."
    },
    "AUR": {
        "buy": "Autonomous driving long-term bet. Entry on technical support.",
        "sell": "Exiting Aurora. Underperformance relative to sector."
    },
    "RZLV": {
        "buy": "Nano-cap speculative play. High volatility setup.",
        "sell": "Stopped out or closing speculative nano-cap position."
    },
    "QBTS": {
        "buy": "Quantum computing speculative entry on volume spike.",
        "sell": "Selling QBTS on technical breakdown of momentum."
    },
    "DYN": {
        "buy": "Biotech catalyst play on clinical trial expectations.",
        "sell": "Exiting DYN after target profit reached."
    },
    "WDC": {
        "buy": "Storage sector cyclical recovery play. Oversold bounce.",
        "sell": "Closing WDC. Sector relative strength weakening."
    }
}

def parse_and_migrate():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    client = create_client(url, key)

    rows = []
    for line in TRADES_DATA.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) < 5: continue
        
        ticker = parts[0]
        action = parts[1].upper()
        shares = int(float(parts[2].replace(',', '')))
        price = float(parts[3])
        ts_str = parts[4]
        
        # Parse timestamp: Dec 31, 2025, 02:51:09 PM
        dt = datetime.strptime(ts_str, "%b %d, %Y, %I:%M:%S %p")
        iso_ts = dt.isoformat()
        
        # Determine reason
        stock_map = REASONING_MAP.get(ticker, {})
        reason = stock_map.get(action.lower(), "Automated trade execution based on technical signals.")

        rows.append({
            "timestamp": iso_ts,
            "ticker": ticker,
            "action": action,
            "shares": shares,
            "price": price,
            "reason": reason
        })

    print(f"Prepared {len(rows)} trades for migration.")
    
    # Supabase allows bulk insert
    try:
        # Insert in chunks of 10 to be safe
        for i in range(0, len(rows), 10):
            chunk = rows[i:i+10]
            client.table("trade_journal").insert(chunk).execute()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    parse_and_migrate()
