import os
from datetime import datetime
from supabase import create_client, Client
import threading

class CloudLog:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client: Client = create_client(self.url, self.key) if self.url and self.key else None
        
    def log(self, level: str, message: str, meta: dict = None):
        """
        Log a message to Supabase.
        Uses a separate thread to prevent blocking the main trading loop.
        """
        if not self.client: return
        
        def _send():
            try:
                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                    "message": message,
                    "meta": meta or {}
                }
                self.client.table("bot_logs").insert(payload).execute()
            except Exception as e:
                print(f"CloudLog Error: {e}")

        # Fire and forget
        thread = threading.Thread(target=_send)
        thread.daemon = True
        thread.start()

    def info(self, message: str, meta: dict = None):
        self.log("INFO", message, meta)

    def warning(self, message: str, meta: dict = None):
        self.log("WARNING", message, meta)
        
    def error(self, message: str, meta: dict = None):
        self.log("ERROR", message, meta) 
