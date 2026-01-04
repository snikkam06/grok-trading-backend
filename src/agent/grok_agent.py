import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict, Any

load_dotenv() # Load variables from .env

class MockResponse:
    def __init__(self, message):
        self.message = message
        self.choices = [type('obj', (object,), {'message': message})]

class MockClient:
    def __init__(self, parent):
        self.parent = parent
        self.chat = self
        self.completions = self.Completions(self)

    class Completions:
        def __init__(self, parent_client):
            self.client = parent_client

        def create(self, model, messages, tools=None, tool_choice=None, temperature=0.7):
            last_msg = messages[-1]
            
            # Check if we are in the 'tool output' phase
            has_price = False
            for m in messages:
                if (isinstance(m, dict) and m.get('role') == 'tool') or \
                   (not isinstance(m, dict) and getattr(m, 'role', '') == 'tool'):
                    has_price = True
            
            if isinstance(last_msg, dict) and last_msg.get('role') == 'tool':
                 has_price = True

            if not has_price:
                print("[MOCK] Deciding to check AAPL price...")
                msg = type('obj', (object,), {
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [
                        type('obj', (object,), {
                            'id': 'call_123',
                            'function': type('obj', (object,), {
                                'name': 'get_stock_price',
                                'arguments': '{"ticker": "AAPL"}'
                            })
                        })
                    ]
                })
                return MockResponse(msg)
            else:
                print("[MOCK] Deciding to BUY AAPL...")
                msg = type('obj', (object,), {
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [
                        type('obj', (object,), {
                            'id': 'call_456',
                            'function': type('obj', (object,), {
                                'name': 'place_trade_orders',
                                'arguments': '{"trades": [{"action": "BUY", "ticker": "AAPL", "shares": 100, "reason": "Mock trade"}]}'
                            })
                        })
                    ]
                })
                return MockResponse(msg)

class GrokTrader:
    def __init__(self, model_name: str = "grok-4-1-fast-reasoning"):
        api_key = os.getenv("XAI_API_KEY")
        base_url = "https://api.x.ai/v1" 
        
        self.mock = False
        if not api_key:
             api_key = os.getenv("OPENAI_API_KEY")
             base_url = None # Default OpenAI
        
        if not api_key:
            print("Alert: No API keys found. Using MOCK Client.")
            self.mock = True
            self.client = MockClient(self)
        else:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            
        self.model = model_name
