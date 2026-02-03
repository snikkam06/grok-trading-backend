#!/usr/bin/env python3
"""
Test script for options data integration.
Verifies connection to webDash database and Schwab client.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from termcolor import colored

load_dotenv()


def test_options_data():
    print(colored("=" * 50, "cyan"))
    print(colored("Testing Options Data Integration", "cyan", attrs=["bold"]))
    print(colored("=" * 50, "cyan"))
    
    # Test 1: Import the module
    print("\n[1] Importing options_data module...")
    try:
        from src.data.options_data import get_sweeps_data, SCHWAB_AVAILABLE, DB_AVAILABLE
        print(colored("  ✓ Module imported successfully", "green"))
        print(f"    Schwab Available: {SCHWAB_AVAILABLE}")
        print(f"    Database Available: {DB_AVAILABLE}")
    except Exception as e:
        print(colored(f"  ✗ Import failed: {e}", "red"))
        return
    
    # Test 2: Get SweepsData instance
    print("\n[2] Getting SweepsData instance...")
    try:
        sd = get_sweeps_data()
        print(colored("  ✓ SweepsData initialized", "green"))
        
        if sd.schwab and sd.schwab.is_authenticated():
            print(colored("  ✓ Schwab client authenticated", "green"))
        else:
            print(colored("  ⚠ Schwab client not authenticated (data fetch may fail)", "yellow"))
    except Exception as e:
        print(colored(f"  ✗ Initialization failed: {e}", "red"))
        return
    
    # Test 3: Fetch active sweeps
    print("\n[3] Fetching active sweeps from database...")
    try:
        sweeps = sd.get_active_sweeps(limit=5)
        print(colored(f"  ✓ Found {len(sweeps)} active sweeps", "green"))
        
        for s in sweeps[:3]:
            print(f"    • {s['ticker']} ${s['strike']} {s['call_put']} exp {s['expiration']} (${s['premium']:,.0f} premium)")
    except Exception as e:
        print(colored(f"  ✗ Failed to fetch sweeps: {e}", "red"))
    
    # Test 4: Fetch option price (if we have sweeps)
    if sweeps:
        print("\n[4] Fetching live option price for first sweep...")
        first = sweeps[0]
        try:
            price = sd.get_option_price(
                first['ticker'],
                first['expiration'],
                first['strike'],
                first['call_put']
            )
            
            if price:
                print(colored(f"  ✓ Got price data for {first['ticker']}", "green"))
                print(f"    Mid: ${price.get('mid', 'N/A')}")
                print(f"    Delta: {price.get('delta', 'N/A')}")
                print(f"    IV: {price.get('iv', 'N/A')}")
                print(f"    Theta: {price.get('theta', 'N/A')}")
            else:
                print(colored("  ⚠ No price data returned (Schwab may not be authenticated)", "yellow"))
        except Exception as e:
            print(colored(f"  ✗ Failed to fetch price: {e}", "red"))
    else:
        print("\n[4] Skipping option price test (no active sweeps)")
    
    # Test 5: Fetch option chain
    print("\n[5] Fetching option chain for SPY...")
    try:
        chain = sd.get_option_chain("SPY")
        
        if chain.get('error'):
            print(colored(f"  ⚠ Chain error: {chain['error']}", "yellow"))
        else:
            print(colored(f"  ✓ Got option chain", "green"))
            print(f"    Calls: {len(chain.get('calls', []))}")
            print(f"    Puts: {len(chain.get('puts', []))}")
            
            if chain.get('calls'):
                top_call = chain['calls'][0]
                print(f"    Sample call: ${top_call.get('strike')} exp {top_call.get('expiration')}")
    except Exception as e:
        print(colored(f"  ✗ Failed to fetch chain: {e}", "red"))
    
    print("\n" + colored("=" * 50, "cyan"))
    print(colored("Test Complete", "cyan", attrs=["bold"]))
    print(colored("=" * 50, "cyan"))


if __name__ == "__main__":
    test_options_data()
