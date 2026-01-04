import os
from supabase import create_client, Client
from datetime import datetime

class ThesisManager:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client: Client = create_client(self.url, self.key) if self.url and self.key else None
        
    def get_active_theses(self) -> str:
        """Fetch all active position theses."""
        if not self.client: return "Thesis DB unavailable."
        
        try:
            res = self.client.table("position_thesis").select("*").eq("is_active", True).execute()
            data = res.data
            if not data:
                return "No active theses."
            
            summary = []
            for item in data:
                summary.append(
                    f"- {item['ticker']}: {item['thesis']} "
                    f"(Stop: ${item.get('invalidation_price')}, Target: ${item.get('target_price')})"
                )
            return "\n".join(summary)
        except Exception as e:
            return f"Error fetching theses: {e}"

    def save_thesis(self, ticker: str, thesis: str, stop: float, target: float):
        """Save a new thesis for a position."""
        if not self.client: return
        
        try:
            # Deactivate old thesis for this ticker if any (simplified logic)
            self.client.table("position_thesis").update({"is_active": False}).eq("ticker", ticker).execute()
            
            payload = {
                "ticker": ticker,
                "thesis": thesis,
                "invalidation_price": stop,
                "target_price": target,
                "is_active": True,
                "entry_date": datetime.now().isoformat()
            }
            self.client.table("position_thesis").insert(payload).execute()
        except Exception as e:
            print(f"Error saving thesis: {e}")

    def close_thesis(self, ticker: str):
        """Mark thesis as inactive when position is closed."""
        if not self.client: return
        try:
            self.client.table("position_thesis").update({"is_active": False}).eq("ticker", ticker).execute()
        except Exception as e:
            print(f"Error closing thesis: {e}")
