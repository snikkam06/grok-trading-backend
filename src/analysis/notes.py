import os
from datetime import datetime
from supabase import create_client, Client

class TradingNotes:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client: Client = create_client(self.url, self.key) if self.url and self.key else None
        
    def get_notes(self) -> str:
        """Fetch the current strategy notes."""
        if not self.client: return "Notes unavailable (No Supabase connection)."
        
        try:
            response = self.client.table("trading_notes").select("content").eq("id", 1).single().execute()
            return response.data['content']
        except Exception as e:
            return f"Error fetching notes: {e}"

    def update_notes(self, new_content: str):
        """Update the notes (overwrite)."""
        if not self.client: return
        
        try:
            self.client.table("trading_notes").update({
                "content": new_content,
                "updated_at": datetime.now().isoformat()
            }).eq("id", 1).execute()
        except Exception as e:
            print(f"Error updating notes: {e}")
            
    def append_notes(self, text_to_append: str):
        """Append text to the existing notes."""
        current = self.get_notes()
        new_content = f"{current}\n- {text_to_append}"
        self.update_notes(new_content)
