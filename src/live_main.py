import os
import json
import time
import sys
import signal
import logging
from datetime import datetime
from dotenv import load_dotenv
from termcolor import colored

from src.data.alpaca_market import AlpacaMarket
from src.data.news import NewsData
from src.portfolio.alpaca_portfolio import AlpacaPortfolio
from src.agent.grok_agent import GrokTrader
import src.analysis.indicators as indicators
from src.analysis.journal import TradingJournal
from src.analysis.notes import TradingNotes
from src.analysis.cloud_log import CloudLog
from src.analysis.thesis import ThesisManager
from src.risk.risk_manager import RiskManager

load_dotenv()

class LiveTrader:
    def __init__(self):
        self.setup_logging()
        self.logger.info("Initializing Grok Live Trader...")
        
        try:
            self.market = AlpacaMarket()
            self.portfolio = AlpacaPortfolio()
            self.news = NewsData()
            self.agent = GrokTrader(model_name="grok-4-1-fast-reasoning")
            self.journal = TradingJournal()
            self.notes = TradingNotes()
            self.cloud_log = CloudLog()
            self.thesis_manager = ThesisManager()
            self.risk_manager = RiskManager(self.portfolio, self.market, self.logger)
        except Exception as e:
            self.logger.critical(f"Initialization Failed: {e}")
            sys.exit(1)
            
        self.running = True
        signal.signal(signal.SIGINT, self.signal_handler)
        self.poll_interval = 600 # 10 minutes

    def setup_logging(self):
        self.logger = logging.getLogger("GrokTrader")
        self.logger.setLevel(logging.INFO)
        
        # Console Handler
        c_handler = logging.StreamHandler()
        c_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(c_handler)
        
        # File Handler
        if not os.path.exists("logs"):
            os.makedirs("logs")
        f_handler = logging.FileHandler(f"logs/trading_{datetime.now().strftime('%Y%m%d')}.log")
        f_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(f_handler)

    def signal_handler(self, sig, frame):
        self.logger.warning("\nShutdown signal received. Exiting gracefully...")
        self.running = False

    def get_market_regime(self):
        """Analyze broad market context (SPY) to determine regime."""
        try:
            spy_hist = self.market.get_history("SPY", days=200)
            if spy_hist is None or spy_hist.empty:
                return "Unknown (Data Unavailable)"
            
            spy_ind = indicators.calculate_indicators(spy_hist)
            latest = indicators.get_latest_indicators(spy_ind)
            
            regime = f"SPY Price: ${latest['price']:.2f} | Trend: {latest['trend']}"
            if latest['rsi'] > 70:
                regime += " | Condition: Overbought"
            elif latest['rsi'] < 30:
                regime += " | Condition: Oversold"
            
            return regime
        except Exception as e:
            self.logger.error(f"Failed to get market regime: {e}")
            return "Unknown (Error)"

    def run(self):
        start_msg = "Grok Live Trading Bot Started (Alpaca Paper)"
        self.logger.info(colored(start_msg, "green", attrs=["bold"]))
        self.cloud_log.info(start_msg, {"event": "startup"})
        
        while self.running:
            now = datetime.now()
            self.logger.info(colored(f"\n--- Checking Market Status at {now.strftime('%H:%M:%S')} ---", "blue"))
            
            if not self.market.is_market_open():
                self.logger.info("Market is closed. Waiting 15 minutes...")
                time.sleep(900)
                continue

            # 1. Gather Context
            portfolio_val = self.portfolio.get_total_value()
            cash = self.portfolio.get_cash()
            holdings = self.portfolio.get_holdings_summary()
            market_regime = self.get_market_regime()
            recent_trades = self.journal.get_recent_entries(limit=5)
            strategy_notes = self.notes.get_notes()
            active_theses = self.thesis_manager.get_active_theses()
            
            self.logger.info(colored(f"PV: ${portfolio_val:.2f} | Cash: ${cash:.2f}", "cyan"))
            self.logger.info(f"Market Regime: {market_regime}")
            self.logger.info(colored(f"Strategy Notes:\n{strategy_notes}", "blue"))

            
            system_prompt = (
                "You are Grok, an elite AI trader specializing in technical analysis for U.S. equities. "
                "You are operating a live trading bot (paper trading) with Alpaca integration.\n\n"

                "OBJECTIVE\n"
                "- Primary: Maximize profit (grow portfolio value).\n"
                "- Secondary: Preserve capital. Your Risk Manager enforces strict rules; do not fight them.\n\n"

                f"MARKET REGIME (SPY context): {market_regime}\n\n"

                "HARD CONSTRAINTS (ENFORCED BY CODE)\n"
                "- Trades per cycle: Max 3.\n"
                "- Position Sizing: Must be $5,000 - $25,000 per trade.\n"
                "- Exposure Cap: Max 20% of portfolio per ticker.\n"
                "- Cooldown: 30-minute lockout after selling a ticker (prevent churn).\n"
                "- No selling more shares than you hold.\n\n"

                "TOOLS AVAILABLE\n"
                "- `scan_market_movers(sort_by)`: Get top gainers/losers/vol from your Universe.\n"
                "- `get_technical_indicators(ticker)`: Get RSI, SMA, Trend for a ticker.\n"
                "- `calculate_risk_size(ticker, stop_loss_pct)`: Get exact share count for risk management.\n"
                "- `search_web(query)`: Look up news/catalysts.\n"
                "- `update_position_thesis(ticker, thesis, ...)`: Save your plan before entering.\n"
                "- `update_shared_notes(content)`: Update global strategy.\n"
                "- `place_trade_orders(trades)`: Execute orders.\n\n"

                "DECISION PROCESS (FOLLOW THIS ORDER)\n"
                "1) **Scan**: Use `scan_market_movers` to find candidates OR check `Active Theses` for management.\n"
                "2) **Verify**: Call `get_technical_indicators` for your top 1-3 candidates.\n"
                "3) **Plan Risk**: If entering new position, call `calculate_risk_size` to find the safe share count.\n"
                "4) **Lock Thesis**: If entering, call `update_position_thesis` to save your reasoning/targets.\n"
                "5) **Execute**: Call `place_trade_orders` (only if indicators confirm setup).\n\n"

                "STRATEGY GUIDELINES\n"
                "- Bullish Regime: Aggressive on pullbacks (RSI < 40). Look for Gainers with high volume.\n"
                "- Bearish Regime: Defensive. Cash is a position. Short rallies (if permitted) or buy deep dips.\n"
                "- **Never trade blindly**. You must see the chart data first.\n\n"

                "JOURNALING REQUIREMENT\n"
                "- Every trade MUST include a concise `reason` referencing fetched data (e.g. \"RSI 35, support at 200 SMA\").\n\n"

                "RECENT TRADES:\n"
                f"{recent_trades}\n\n"

                "SHARED NOTES (Strategy Context):\n"
                f"{strategy_notes}\n\n"

                "ACTIVE THESES (Do not violate these):\n"
                f"{active_theses}\n\n"

                "OUTPUT RULE\n"
                "- If no intended trade, output a short thought on why, then stop.\n"
                "- If trading, use the tools. Do not just talk about it.\n"
            )
            
            user_prompt = (
                f"Portfolio: ${portfolio_val:.2f}, Cash: ${cash:.2f}\n"
                f"Holdings: {holdings}\n"
                "Scan the market, check charts of potential candidates, execute trades, and update shared notes if you learn something new."
            )

            # 3. Agent Loop
            self.run_agent_loop(system_prompt, user_prompt)
            
            # Wait for next cycle
            for _ in range(self.poll_interval):
                if not self.running: break
                time.sleep(1)

    def run_agent_loop(self, system_prompt, user_prompt):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        tools = self.get_tools()
        
        MAX_TURNS = 10
        for turn in range(MAX_TURNS):
            try:
                response = self.agent.client.chat.completions.create(
                    model=self.agent.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
            except Exception as e:
                self.logger.error(f"Agent API Error: {e}")
                break

            msg = response.choices[0].message
            
            if not msg.content and not msg.tool_calls:
                break
                
            messages.append(msg)
            
            if msg.tool_calls:
                self.handle_tool_calls(msg.tool_calls, messages)
            else:
                if msg.content:
                    self.logger.info(f"Grok: {msg.content[:200]}...")
                
                # Heuristic stop
                if "no trade" in (msg.content or "").lower():
                    break

    def get_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_stock_price",
                    "description": "Get latest price",
                    "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_technical_indicators",
                    "description": "Get RSI, SMA, and trend data for a stock.",
                    "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search for news/catalysts.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_risk_size",
                    "description": "Calculate share size based on ATR volatility risk.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "stop_loss_pct": {"type": "number", "description": "Stop loss percentage (e.g., 0.02 for 2%)"},
                            "risk_pct": {"type": "number", "description": "Portfolio risk percentage (default 0.01 for 1%)"}
                        },
                        "required": ["ticker", "stop_loss_pct"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scan_market_movers",
                    "description": "Scan Candidate Universe for top gainers/losers/volume.",
                    "parameters": {"type": "object", "properties": {"sort_by": {"type": "string", "enum": ["gainers", "losers", "volume"]}}, "required": ["sort_by"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_position_thesis",
                    "description": "Save a strategic plan for a ticker (Required before new generic entry).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "thesis": {"type": "string", "description": "Why we are entering (Technical/Fundamental reason)."},
                            "stop_loss_price": {"type": "number"},
                            "target_price": {"type": "number"}
                        },
                        "required": ["ticker", "thesis", "stop_loss_price", "target_price"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "place_trade_orders",
                    "description": "Submit orders with mandatory reasoning.",
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
                                        "reason": {"type": "string", "description": "Short explanation for this trade implementation."}
                                    },
                                    "required": ["action", "ticker", "shares", "reason"]
                                }
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_shared_notes",
                    "description": "Update the persistent strategy notes. Use this to refine your strategy or leave notes for next cycle.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The FULL new content of the notes (this overwrites existing notes, so include old important stuff if needed, or just append)."
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["overwrite", "append"],
                                "description": "Whether to replace all notes or just add to the end."
                            }
                        },
                        "required": ["content", "mode"]
                    }
                }
            }
        ]

    def handle_tool_calls(self, tool_calls, messages):
        for tc in tool_calls:
            fname = tc.function.name
            args = json.loads(tc.function.arguments)
            res_content = ""
            
            try:
                if fname == "get_stock_price":
                    ticker = args['ticker'].upper()
                    price = self.market.get_price(ticker)
                    res_content = f"{ticker}: ${price}"
                    self.logger.info(f"  > Checked Price {ticker}: {price}")
                    
                elif fname == "get_technical_indicators":
                    ticker = args['ticker'].upper()
                    hist = self.market.get_history(ticker, days=100)
                    if hist is not None:
                        ind = indicators.calculate_indicators(hist)
                        data = indicators.get_latest_indicators(ind)
                        res_content = json.dumps(data)
                        self.logger.info(f"  > Analysis {ticker}: RSI={data['rsi']}, Trend={data['trend']}")
                    else:
                        res_content = "Data unavailable"
                        
                elif fname == "search_web":
                    q = args['query']
                    res = self.news.search_web(q)
                    res_content = res
                    self.logger.info(f"  > Searched: {q}")
                    
                elif fname == "calculate_risk_size":
                    ticker = args['ticker'].upper()
                    stop_pct = float(args['stop_loss_pct'])
                    risk_pct = float(args.get('risk_pct', 0.005)) # Default 0.5% risk
                    
                    price = self.market.get_price(ticker)
                    portfolio_val = self.portfolio.get_total_value()
                    
                    # Risk Math: (Portfolio * Risk%) / (Price * Stop%)
                    risk_amt = portfolio_val * risk_pct
                    risk_per_share = price * stop_pct
                    shares = int(risk_amt / risk_per_share)
                    
                    res_content = json.dumps({
                        "ticker": ticker,
                        "price": price,
                        "risk_amt": risk_amt,
                        "recommended_shares": shares,
                        "note": f"Based on {risk_pct*100}% portfolio risk and {stop_pct*100}% stop width."
                    })
                    self.logger.info(colored(f"  > Sizing Calc {ticker}: {shares} shares (Risk ${risk_amt:.0f})", "cyan"))
                
                elif fname == "update_position_thesis":
                    ticker = args['ticker'].upper()
                    thesis = args['thesis']
                    stop = float(args['stop_loss_price'])
                    target = float(args['target_price'])
                    
                    self.thesis_manager.save_thesis(ticker, thesis, stop, target)
                    self.logger.info(colored(f"  > Thesis Saved for {ticker}: Stop ${stop}, Target ${target}", "magenta"))
                    self.cloud_log.info(f"THESIS: {ticker}", {"thesis": thesis, "stop": stop, "target": target})
                    res_content = f"Thesis saved for {ticker}."

                elif fname == "scan_market_movers":
                    sort_by = args['sort_by']
                    # Use the same universe defined in run()
                    universe = list(set(list(self.portfolio.get_positions().keys()) + [
                        "SPY", "QQQ", "IWM", "NVDA", "AAPL", "MSFT", "AMD", "TSLA", "AMZN", 
                        "JPM", "XOM", "LLY", "COIN", "MSTR"
                    ]))
                    
                    snaps = self.market.get_snapshots(universe)
                    # Convert to list
                    data = []
                    for t, s in snaps.items():
                        data.append({"ticker": t, "change": s['change_pct'], "price": s['price'], "vol": s['volume']})
                    
                    if sort_by == 'gainers':
                        data.sort(key=lambda x: x['change'], reverse=True)
                    elif sort_by == 'losers':
                        data.sort(key=lambda x: x['change'])
                    elif sort_by == 'volume':
                        data.sort(key=lambda x: x['vol'], reverse=True)
                        
                    res_content = json.dumps(data[:5]) # Top 5
                    self.logger.info(f"  > Screener ({sort_by}): {res_content}")
                    
                elif fname == "place_trade_orders":
                    trades = args.get('trades', [])
                    
                    # Hardware Limit: Max 3 trades per cycle
                    if len(trades) > 3:
                        self.logger.warning(colored(f"  > Capping trade count at 3 (requested {len(trades)})", "yellow"))
                        trades = trades[:3]

                    self.logger.info(colored(f"  > Executing {len(trades)} trades...", "green"))
                    for t in trades:
                        # Risk Check
                        allowed, rejection_reason = self.risk_manager.validate_order(t['ticker'], t['action'], int(t['shares']))
                        
                        if not allowed:
                            self.logger.warning(colored(f"    x Risk Rejected: {t['ticker']} - {rejection_reason}", "red"))
                            self.cloud_log.warning(f"RISK REJECT: {t['ticker']}", {"reason": rejection_reason})
                            res_content += f"Trade {t['ticker']} REJECTED: {rejection_reason}. "
                            continue

                        # Execute if allowed
                        self.portfolio.execute_trade(t['ticker'], t['action'], int(t['shares']))
                        
                        # Log to Journal
                        price = self.market.get_price(t['ticker']) or 0.0
                        reason = t.get('reason', 'No reason provided')
                        self.journal.log_trade(t['ticker'], t['action'], int(t['shares']), price, reason)
                        self.logger.info(f"    - Journaled: {t['action']} {t['ticker']} ({reason})")
                        
                        # Cloud Log
                        self.cloud_log.info(f"TRADE: {t['action']} {t['shares']} {t['ticker']}", {
                            "ticker": t['ticker'],
                            "action": t['action'],
                            "shares": int(t['shares']),
                            "price": price,
                            "reason": reason
                        })
                        
                    if not res_content:
                        res_content = "All orders submitted and logged to journal."

                elif fname == "update_shared_notes":
                    content = args['content']
                    mode = args.get('mode', 'append')
                    
                    if mode == 'overwrite':
                        self.notes.update_notes(content)
                        self.logger.info(colored(f"  > Notes Overwritten: {content[:50]}...", "magenta"))
                    else:
                        self.notes.append_notes(content)
                        self.logger.info(colored(f"  > Notes Appended: {content[:50]}...", "magenta"))
                    
                    self.cloud_log.info("Strategy Notes Updated", {"mode": mode, "preview": content[:100]})
                        
                    res_content = "Strategy notes updated."
                    
            except Exception as e:
                res_content = f"Tool Error: {e}"
                self.logger.error(res_content)
                self.cloud_log.error(f"Tool Error: {fname}", {"error": str(e)})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": res_content
            })

if __name__ == "__main__":
    bot = LiveTrader()
    bot.run()
