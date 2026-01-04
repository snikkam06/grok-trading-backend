import os
import json
import time
from datetime import datetime, timedelta
import pandas as pd
from termcolor import colored

from src.data.market import MarketData
from src.data.news import NewsData
from src.portfolio.portfolio import Portfolio
from src.agent.grok_agent import GrokTrader

# Configuration
START_DATE = datetime(2025, 2, 1)
END_DATE = datetime(2025, 2, 5) # or datetime.now() if running live-ish
# For reproduction purposes, if 2025 data doesn't exist yet (since we are in 2024/2025 transition?), 
# We might need to adjust dates to "Recent Past" ex: Feb 2024 - Oct 2024 for a valid cache.
# The user prompt says "Feb-Oct 2025" which is future relative to 'current' world but 'past' in the prompt's context.
# However, yfinance only has real data. If today is Dec 2025 (per metadata), then 2025 data exists.
# Metadata says: 2025-12-30. So Feb-Oct 2025 is in the PAST. We are good.

class Simulation:
    def __init__(self):
        self.market = MarketData(START_DATE, END_DATE)
        self.news = NewsData()
        self.portfolio = Portfolio()
        self.agent = GrokTrader(model_name="grok-beta") 
        self.current_date = START_DATE
        self.daily_logs = []

    def get_agent_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_stock_price",
                    "description": "Get the current closing price of a stock ticker.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "The stock ticker symbol (e.g. AAPL)"}
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_market_news",
                    "description": "Get news headlines for the current date.",
                    "parameters": {
                        "type": "object",
                        "properties": {}, # No args needed, implied current date
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "place_trade_orders",
                    "description": "Place buy or sell orders for the day. Call this ONLY when you differ on final decisions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "trades": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "action": {"type": "string", "enum": ["BUY", "SELL"]},
                                        "ticker": {"type": "string"},
                                        "shares": {"type": "integer"},
                                        "reason": {"type": "string"}
                                    },
                                    "required": ["action", "ticker", "shares", "reason"]
                                }
                            }
                        },
                        "required": ["trades"]
                    }
                }
            }
        ]

    def run_day(self):
        # 1. Update context
        self.market.set_simulation_date(self.current_date)
        
        # Skip weekends/holidays (simple check, yfinance data check handles the rest)
        # Actually simplest is: check if SPY has a price today.
        spy_price = self.market.get_price("SPY")
        if spy_price is None:
            print(f"[{self.current_date.date()}] Market closed. Skipping.")
            return

        # 2. Calculating Portfolio Value
        # We need current prices for all holdings to get NAV
        current_prices = {}
        for ticker in self.portfolio.positions:
            p = self.market.get_price(ticker)
            if p: current_prices[ticker] = p
            
        total_value = self.portfolio.get_total_value(current_prices)
        cash = self.portfolio.cash
        holdings_str = self.portfolio.get_holdings_summary()
        
        print(colored(f"\n--- Date: {self.current_date.date()} | PV: ${total_value:.2f} | Cash: ${cash:.2f} ---", "cyan"))

        # 3. Construct System Prompt
        system_prompt = (
            "You are Grok, an expert AI portfolio manager. "
            "Your goal is to maximize returns over an 8-month period. "
            "You have strict risk constraints: Min trade $5k, Max trade $25k per stock. "
            "Do not hallucinate prices. Use 'get_stock_price' to check data before trading. "
            "Use 'place_trade_orders' to submit your final decisions for the day."
        )
        
        user_prompt = (
            f"Current Date: {self.current_date.date()}\n"
            f"Portfolio Value: ${total_value:.2f}\n"
            f"Cash Available: ${cash:.2f}\n"
            f"Current Holdings: {holdings_str}\n\n"
            "Analyze the market and current positions. "
            "You can look up prices of stocks you are interested in (e.g. MAG7, popular tech, etc). "
            "Decide on trades."
        )

        # 4. Agent Loop (Tool Usage)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Limit max turns to prevent infinite loops (cost safety)
        MAX_TURNS = 5 
        
        for turn in range(MAX_TURNS):
            response = self.agent.client.chat.completions.create(
                model=self.agent.model,
                messages=messages,
                tools=self.get_agent_tools(),
                tool_choice="auto"
            )
            
            msg = response.choices[0].message
            messages.append(msg)
            
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    result_content = ""
                    
                    if func_name == "get_stock_price":
                        ticker = args.get("ticker", "").upper()
                        price = self.market.get_price(ticker)
                        # also get history for context
                        # hist = self.market.get_history(ticker, days=5) 
                        if price:
                            result_content = f"{ticker} Price on {self.current_date.date()}: ${price:.2f}"
                        else:
                            result_content = f"Price for {ticker} not available (market closed or invalid)."
                        print(f"  > Agent checked {ticker}: ${price}")

                    elif func_name == "get_market_news":
                        news_txt = self.news.get_news(self.current_date)
                        result_content = f"News: {news_txt}"
                        print(f"  > Agent checked news.")

                    elif func_name == "place_trade_orders":
                        trades = args.get("trades", [])
                        print(colored(f"  > Agent submitting {len(trades)} trades...", "green"))
                        for t in trades:
                            ticker = t['ticker'].upper()
                            action = t['action'].upper()
                            shares = int(t['shares'])
                            
                            # Re-verify price for execution
                            # We execute at CLOSE price of the day (which we know because it's backtest)
                            price = self.market.get_price(ticker)
                            if price:
                                success = self.portfolio.execute_trade(ticker, action, shares, price, self.current_date)
                            else:
                                print(f"    Failed to execute {ticker}: No price.")
                        
                        # End the turn loop after trading (assuming ONE batch of trades per day)
                        return

                    # Feed back the tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_content
                    })
            else:
                # No tool called, just thought/text.
                print(f"  > Agent thought: {msg.content}")
                # If agent just talks and doesn't trade, we break after it says something, 
                # or we force it to finalize?
                # For now, let it talk, loops until max turns or it calls place_trade_orders
                if "no trade" in msg.content.lower():
                     return

        # End of Day logging
        self.daily_logs.append({
            "date": str(self.current_date.date()),
            "pv": total_value,
            "cash": cash
        })

    def run(self):
        print(f"Starting Simulation from {START_DATE.date()} to {END_DATE.date()}")
        while self.current_date <= END_DATE:
            self.run_day()
            self.current_date += timedelta(days=1)
        
        print("Simulation Complete.")
        # Save logs
        with open("logs/sim_results.json", "w") as f:
            json.dump(self.daily_logs, f, indent=2)

if __name__ == "__main__":
    if not os.path.exists("logs"): os.makedirs("logs")
    sim = Simulation()
    sim.run()
