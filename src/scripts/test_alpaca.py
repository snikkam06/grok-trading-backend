import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from termcolor import colored

load_dotenv()

def test_alpaca_connection():
    api_key = os.getenv('APCA_API_KEY_ID')
    secret_key = os.getenv('APCA_API_SECRET_KEY')
    
    if not api_key or not secret_key:
        print(colored("Error: Alpaca API keys not found in .env", "red"))
        return

    try:
        client = TradingClient(api_key, secret_key, paper=True)
        account = client.get_account()
        print(colored("SUCCESS! Connected to Alpaca.", "green"))
        print(f"Account Balance: ${account.cash}")
        print(f"Portfolio Value: ${account.portfolio_value}")
        print(f"Trading Blocked: {account.trading_blocked}")
    except Exception as e:
        print(colored(f"Connection Failed: {e}", "red"))

if __name__ == "__main__":
    test_alpaca_connection()
