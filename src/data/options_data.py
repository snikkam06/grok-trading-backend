"""
Options data module for grokTrading.
Connects to sweepAutomation/webDash database for options sweeps data
and uses Schwab client for live options pricing and Greeks.
"""
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add webDash to path for shared modules
WEBDASH_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'webDash')
sys.path.insert(0, WEBDASH_PATH)

try:
    from schwab_client import get_schwab_client, build_option_symbol
    SCHWAB_AVAILABLE = True
except ImportError:
    SCHWAB_AVAILABLE = False
    print("Warning: Schwab client not available from webDash")

# Import webDash database functions
try:
    from db import get_db, fix_sql, IS_POSTGRES
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: webDash database module not available")


class SweepsData:
    """Interface to sweepAutomation options sweeps data."""
    
    def __init__(self):
        self.schwab = get_schwab_client() if SCHWAB_AVAILABLE else None
    
    def get_active_sweeps(self, limit: int = 20) -> List[Dict]:
        """
        Get active (non-expired) options sweeps from Discord signals.
        Returns list of contracts with current pricing data.
        """
        if not DB_AVAILABLE:
            return []
        
        conn = get_db()
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Fetch active contracts (not expired)
        sql = """
            SELECT c.id, c.ticker, c.strike, c.premium, c.call_put, 
                   c.expiration, c.signal_time, c.orders,
                   c.stock_price_at_signal, c.option_price_at_signal
            FROM contracts c
            WHERE c.expiration IS NOT NULL
            ORDER BY c.signal_time DESC
        """
        cursor.execute(fix_sql(sql))
        rows = cursor.fetchall()
        conn.close()
        
        # Filter to active only (expiration >= today)
        active = []
        for row in rows:
            contract = dict(row)
            exp = contract.get('expiration')
            if not exp:
                continue
            try:
                parts = exp.split('/')
                exp_date = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                if exp_date >= today:
                    active.append(contract)
            except:
                continue
            
            if len(active) >= limit:
                break
        
        return active
    
    def get_sweeps_by_ticker(self, ticker: str) -> List[Dict]:
        """Get all active sweeps for a specific ticker."""
        sweeps = self.get_active_sweeps(limit=100)
        return [s for s in sweeps if s['ticker'].upper() == ticker.upper()]
    
    def get_option_price(self, ticker: str, expiration: str, strike: float, call_put: str) -> Optional[Dict]:
        """
        Get current option mid price and Greeks from Schwab.
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL')
            expiration: Expiration date in MM/DD/YYYY format
            strike: Strike price
            call_put: 'Call' or 'Put'
            
        Returns:
            Dict with 'mid', 'last', 'iv', 'delta', 'gamma', 'theta', 'vega', 'rho'
        """
        if not self.schwab or not self.schwab.is_authenticated():
            return None
        
        return self.schwab.get_option_mid_price(ticker, expiration, strike, call_put)
    
    def get_option_chain(self, ticker: str, expiration: str = None) -> Dict[str, Any]:
        """
        Get full option chain for a ticker.
        
        Args:
            ticker: Stock symbol
            expiration: Optional specific expiration date (MM/DD/YYYY)
            
        Returns:
            Dict with 'calls' and 'puts' lists
        """
        if not self.schwab or not self.schwab.is_authenticated():
            return {"calls": [], "puts": [], "error": "Schwab not authenticated"}
        
        try:
            from schwab.client import Client
            from datetime import timedelta
            
            if expiration:
                # Parse the expiration date
                parts = expiration.split('/')
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                if year < 100:
                    year += 2000
                from_date = datetime(year, month, day)
                to_date = from_date + timedelta(days=1)
            else:
                # Get next 30 days of expirations
                from_date = datetime.now()
                to_date = from_date + timedelta(days=30)
            
            response = self.schwab.client.get_option_chain(
                symbol=ticker,
                contract_type=Client.Options.ContractType.ALL,
                strategy=Client.Options.Strategy.SINGLE,
                from_date=from_date,
                to_date=to_date
            )
            
            if response.status_code != 200:
                return {"calls": [], "puts": [], "error": f"API error: {response.status_code}"}
            
            chain = response.json()
            
            # Parse calls
            calls = []
            for exp_key, strikes in chain.get('callExpDateMap', {}).items():
                for strike_key, opts in strikes.items():
                    if opts:
                        opt = opts[0]
                        calls.append({
                            'expiration': exp_key.split(':')[0],
                            'strike': float(strike_key),
                            'bid': opt.get('bid'),
                            'ask': opt.get('ask'),
                            'mid': (opt.get('bid', 0) + opt.get('ask', 0)) / 2,
                            'last': opt.get('last'),
                            'volume': opt.get('totalVolume'),
                            'iv': opt.get('volatility'),
                            'delta': opt.get('delta'),
                            'gamma': opt.get('gamma'),
                            'theta': opt.get('theta'),
                        })
            
            # Parse puts
            puts = []
            for exp_key, strikes in chain.get('putExpDateMap', {}).items():
                for strike_key, opts in strikes.items():
                    if opts:
                        opt = opts[0]
                        puts.append({
                            'expiration': exp_key.split(':')[0],
                            'strike': float(strike_key),
                            'bid': opt.get('bid'),
                            'ask': opt.get('ask'),
                            'mid': (opt.get('bid', 0) + opt.get('ask', 0)) / 2,
                            'last': opt.get('last'),
                            'volume': opt.get('totalVolume'),
                            'iv': opt.get('volatility'),
                            'delta': opt.get('delta'),
                            'gamma': opt.get('gamma'),
                            'theta': opt.get('theta'),
                        })
            
            return {"calls": calls, "puts": puts}
            
        except Exception as e:
            return {"calls": [], "puts": [], "error": str(e)}
    
    def get_greeks_history(self, contract_id: int) -> List[Dict]:
        """Get Greeks history for a specific contract from the database."""
        if not DB_AVAILABLE:
            return []
        
        conn = get_db()
        cursor = conn.cursor()
        
        sql = """
            SELECT date, time_of_day, implied_volatility, delta, gamma, theta, vega, rho
            FROM option_greeks
            WHERE contract_id = ?
            ORDER BY date ASC, time_of_day ASC
        """
        cursor.execute(fix_sql(sql), (contract_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_stock_quote(self, ticker: str) -> Optional[Dict]:
        """Get current stock quote from Schwab."""
        if not self.schwab or not self.schwab.is_authenticated():
            return None
        
        return self.schwab.get_quote(ticker)


# Singleton instance
_sweeps_data = None

def get_sweeps_data() -> SweepsData:
    """Get singleton instance of SweepsData."""
    global _sweeps_data
    if _sweeps_data is None:
        _sweeps_data = SweepsData()
    return _sweeps_data


if __name__ == "__main__":
    # Quick test
    sd = get_sweeps_data()
    
    print("Testing sweeps data...")
    sweeps = sd.get_active_sweeps(limit=5)
    print(f"Found {len(sweeps)} active sweeps")
    for s in sweeps[:3]:
        print(f"  {s['ticker']} {s['strike']} {s['call_put']} exp {s['expiration']}")
    
    if sweeps:
        first = sweeps[0]
        print(f"\nFetching live price for {first['ticker']}...")
        price = sd.get_option_price(
            first['ticker'], 
            first['expiration'], 
            first['strike'], 
            first['call_put']
        )
        if price:
            print(f"  Mid: ${price.get('mid')}, Delta: {price.get('delta')}, IV: {price.get('iv')}")
        else:
            print("  Price not available")
