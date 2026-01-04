import os
import json
from datetime import datetime
from typing import List, Dict
from supabase import create_client, Client

class TradingJournal:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            print("Warning: Supabase credentials not found. Using local fallback.")
            self.client = None
            self.local_file = "trade_journal.json"
            if not os.path.exists(self.local_file):
                with open(self.local_file, 'w') as f: json.dump([], f)
        else:
            self.client: Client = create_client(self.url, self.key)

    def log_trade(self, ticker: str, action: str, shares: int, price: float, reason: str):
        """Log a trade with its context and reasoning."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "action": action,
            "shares": shares,
            "price": price,
            "reason": reason
        }
        
        if self.client:
            try:
                self.client.table("trade_journal").insert(entry).execute()
            except Exception as e:
                print(f"Supabase Error: {e}. Falling back to local.")
                self._log_local(entry)
        else:
            self._log_local(entry)

    def _log_local(self, entry):
        try:
            with open(self.local_file, 'r') as f:
                history = json.load(f)
        except: history = []
        
        history.append(entry)
        if len(history) > 100: history = history[-100:]
        
        with open(self.local_file, 'w') as f:
            json.dump(history, f, indent=2)

    def get_history(self) -> List[Dict]:
        """Get full journal history."""
        if self.client:
            try:
                response = self.client.table("trade_journal").select("*").order("timestamp", desc=True).limit(100).execute()
                # Return reversed to keep chronological order if needed, or just return as is.
                # Usually prompts want recent at bottom, or just a list. 
                # Let's verify data structure. Supabase returns .data
                return response.data
            except Exception as e:
                print(f"Supabase Read Error: {e}")
                return self._get_local_history()
        else:
            return self._get_local_history()

    def _get_local_history(self):
        try:
            with open(self.local_file, 'r') as f:
                return json.load(f)
        except: return []

    def get_recent_entries(self, limit=5) -> str:
        """Get formatted string of recent trades for LLM context."""
        history = self.get_history()
        if not history:
            return "No previous trades recorded."
            
        # If history comes from Supabase desc sort, top one is most recent.
        # If local, it's chronological (append).
        # We need to standardize.
        
        # Let's assume history is a list of dicts.
        # Sort by timestamp to be safe.
        history.sort(key=lambda x: x['timestamp'])
        
        recent = history[-limit:]
        formatted = []
        for entry in recent:
            # Handle slight format differences if needed
            ts_str = entry['timestamp']
            # Supabase might return full ISO with Z, local might not. 
            try:
                dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except:
                dt = datetime.now() # Fallback
                
            ts = dt.strftime('%Y-%m-%d %H:%M')
            formatted.append(
                f"[{ts}] {entry['action']} {entry['shares']} {entry['ticker']} @ ${float(entry['price']):.2f} | Reason: {entry['reason']}"
            )
        return "\n".join(formatted)
