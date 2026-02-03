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
from src.data.options_data import get_sweeps_data
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
            self.sweeps = get_sweeps_data()  # Options sweeps data
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
                "You are Grok, an elite AI trader specializing in technical analysis for U.S. equities AND stock options. "
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

                "STOCK TRADING TOOLS\n"
                "- `scan_market_movers(sort_by)`: Get top gainers/losers/vol from your Universe.\n"
                "- `get_technical_indicators(ticker)`: Get RSI, SMA, Trend for a ticker.\n"
                "- `calculate_risk_size(ticker, stop_loss_pct)`: Get exact share count for risk management.\n"
                "- `search_web(query)`: Look up news/catalysts.\n"
                "- `update_position_thesis(ticker, thesis, ...)`: Save your plan before entering.\n"
                "- `update_shared_notes(content)`: Overwrite global strategy with a concise summary.\n"
                "- `place_trade_orders(trades)`: Execute stock orders.\n\n"
                
                "OPTIONS TRADING TOOLS (NEW!)\n"
                "- `get_active_sweeps(ticker?, limit?)`: Get institutional options flow from Discord signals. Large premium sweeps often indicate smart money direction.\n"
                "- `get_option_price(ticker, expiration, strike, call_put)`: Get current mid price + Greeks (IV, delta, gamma, theta).\n"
                "- `get_option_chain(ticker, expiration?)`: Get full option chain with top contracts by volume.\n\n"

                "DECISION PROCESS (FOLLOW THIS ORDER)\n"
                "1) **Scan**: Use `scan_market_movers` OR `get_active_sweeps` to find candidates.\n"
                "2) **Verify**: Call `get_technical_indicators` for stocks, `get_option_price` for options.\n"
                "3) **Plan Risk**: Call `calculate_risk_size` for stocks. For options, check delta/theta decay.\n"
                "4) **Lock Thesis**: Call `update_position_thesis` to save reasoning/targets.\n"
                "5) **Execute**: Call `place_trade_orders` (only if indicators confirm setup).\n\n"

                "OPTIONS STRATEGY GUIDELINES\n"
                "- **Follow the Sweeps**: Large premium sweeps (>$500K) often signal institutional conviction.\n"
                "- **Delta Rule**: For directional plays, prefer delta 0.30-0.50 for balance of leverage and probability.\n"
                "- **Theta Decay**: Avoid holding options <7 DTE unless you have strong conviction.\n"
                "- **IV Awareness**: High IV = expensive options. Post-earnings IV crush can hurt long positions.\n"
                "- **Greeks Check**: Always verify delta, theta before entering. High gamma near expiry = high risk.\n\n"

                "STOCK STRATEGY GUIDELINES\n"
                "- Bullish Regime: Aggressive on pullbacks (RSI < 40). Look for Price > VWAP confirmation.\n"
                "- Bearish Regime: Defensive. Cash is a position. Short rallies (if permitted) or buy deep dips.\n"
                "- **VWAP Rule**: Avoid buying if Price is > 3% above VWAP (chasing). Prefer entries near VWAP support.\n"
                "- **News Rule**: Before trading big movers, call `search_web` with specific queries like '{ticker} stock catalyst today'.\n"
                "- **Never trade blindly**. You must see the chart data first.\n\n"

                "JOURNALING REQUIREMENT\n"
                "- Every trade MUST include a concise `reason` referencing fetched data (e.g. \"RSI 35, support at 200 SMA\" or \"Large call sweep $1.2M, delta 0.45\").\n\n"

                "RECENT TRADES:\n"
                f"{recent_trades}\n\n"

                "SHARED NOTES (Strategy Context):\n"
                f"{strategy_notes}\n\n"
                "NOTE MAINTENANCE RULE:\n"
                "- Do NOT append individual trade logs or price history to Shared Notes.\n"
                "- Maintain a concise 3-5 bullet summary of your CURRENT stance (e.g., 'Bullish, buying dips in semi-conductors').\n"
                "- Use 'overwrite' mode to clear old stale data.\n\n"

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
            self.logger.info(colored(f"Cycle complete. Sleeping for {self.poll_interval // 60} minutes...", "yellow"))
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
                    "description": "Overwrite the global strategy notes. maintain a CONCISE summary of the market regime and current plan.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The new summary note (e.g. 'Market is oversold, looking for tech bounces'). Replaces old notes."
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["overwrite", "append"],
                                "description": "Always use 'overwrite' to keep notes clean, unless adding a critical specific alert."
                            }
                        },
                        "required": ["content", "mode"]
                    }
                }
            },
            # ===== OPTIONS TRADING TOOLS =====
            {
                "type": "function",
                "function": {
                    "name": "get_active_sweeps",
                    "description": "Get active options sweeps from Discord signals (large institutional flow). Returns list of contracts with ticker, strike, expiration, call/put, premium.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Optional: Filter sweeps by ticker symbol. Leave empty for all active sweeps."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max number of sweeps to return (default 10)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_option_price",
                    "description": "Get current mid price and Greeks (IV, delta, gamma, theta) for a specific option contract.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Stock symbol (e.g., AAPL)"},
                            "expiration": {"type": "string", "description": "Expiration date in MM/DD/YYYY format"},
                            "strike": {"type": "number", "description": "Strike price"},
                            "call_put": {"type": "string", "enum": ["Call", "Put"], "description": "Option type"}
                        },
                        "required": ["ticker", "expiration", "strike", "call_put"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_option_chain",
                    "description": "Get full option chain (calls and puts) for a ticker. Use to analyze available strikes and expirations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Stock symbol"},
                            "expiration": {"type": "string", "description": "Optional: Specific expiration (MM/DD/YYYY). If omitted, returns next 30 days."}
                        },
                        "required": ["ticker"]
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
                        self.logger.info(f"  > Analysis {ticker}: RSI={data['rsi']}, VWAP=${data.get('vwap',0)}, Trend={data['trend']}")
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
                
                # ===== OPTIONS TRADING TOOL HANDLERS =====
                elif fname == "get_active_sweeps":
                    ticker = args.get('ticker', '').upper() if args.get('ticker') else None
                    limit = int(args.get('limit', 10))
                    
                    if ticker:
                        sweeps = self.sweeps.get_sweeps_by_ticker(ticker)
                    else:
                        sweeps = self.sweeps.get_active_sweeps(limit=limit)
                    
                    # Format for agent consumption
                    formatted = []
                    for s in sweeps[:limit]:
                        formatted.append({
                            'id': s['id'],
                            'ticker': s['ticker'],
                            'strike': s['strike'],
                            'type': s['call_put'],
                            'expiration': s['expiration'],
                            'premium': s['premium'],
                            'orders': s['orders'],
                            'signal_price': s.get('option_price_at_signal')
                        })
                    
                    res_content = json.dumps(formatted, indent=2)
                    self.logger.info(colored(f"  > Active Sweeps: Found {len(formatted)} contracts", "cyan"))
                
                elif fname == "get_option_price":
                    ticker = args['ticker'].upper()
                    expiration = args['expiration']
                    strike = float(args['strike'])
                    call_put = args['call_put']
                    
                    price_data = self.sweeps.get_option_price(ticker, expiration, strike, call_put)
                    
                    if price_data:
                        res_content = json.dumps({
                            'ticker': ticker,
                            'strike': strike,
                            'type': call_put,
                            'expiration': expiration,
                            'mid': price_data.get('mid'),
                            'last': price_data.get('last'),
                            'iv': price_data.get('iv'),
                            'delta': price_data.get('delta'),
                            'gamma': price_data.get('gamma'),
                            'theta': price_data.get('theta'),
                            'vega': price_data.get('vega')
                        })
                        self.logger.info(colored(
                            f"  > Option Price {ticker} {strike} {call_put}: Mid=${price_data.get('mid')}, Delta={price_data.get('delta')}", 
                            "cyan"
                        ))
                    else:
                        res_content = json.dumps({"error": "Could not fetch option price. Schwab may not be authenticated."})
                        self.logger.warning(f"  > Failed to fetch option price for {ticker}")
                
                elif fname == "get_option_chain":
                    ticker = args['ticker'].upper()
                    expiration = args.get('expiration')
                    
                    chain = self.sweeps.get_option_chain(ticker, expiration)
                    
                    if chain.get('error'):
                        res_content = json.dumps({"error": chain['error']})
                        self.logger.warning(f"  > Option chain error: {chain['error']}")
                    else:
                        # Summarize for agent (limit to top 10 each by volume)
                        calls = sorted(chain.get('calls', []), key=lambda x: x.get('volume') or 0, reverse=True)[:10]
                        puts = sorted(chain.get('puts', []), key=lambda x: x.get('volume') or 0, reverse=True)[:10]
                        
                        res_content = json.dumps({
                            'ticker': ticker,
                            'top_calls': calls,
                            'top_puts': puts,
                            'total_calls': len(chain.get('calls', [])),
                            'total_puts': len(chain.get('puts', []))
                        }, indent=2)
                        self.logger.info(colored(
                            f"  > Option Chain {ticker}: {len(chain.get('calls', []))} calls, {len(chain.get('puts', []))} puts",
                            "cyan"
                        ))
                    
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
