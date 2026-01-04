import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def seed_journal():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: Supabase credentials missing.")
        return

    client = create_client(url, key)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "ticker": "CASH",
        "action": "DEPOSIT",
        "shares": 0,
        "price": 100000.0,
        "reason": "Initial capital deposit for Grok Trading System."
    }
    
    try:
        response = client.table("trade_journal").insert(entry).execute()
        print("Successfully seeded database with initial entry.")
        print(response.data)
    except Exception as e:
        print(f"Error seeding database: {e}")

if __name__ == "__main__":
    seed_journal()
