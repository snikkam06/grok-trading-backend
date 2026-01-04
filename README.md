# GrokTrade: The AI-Driven Quantitative Trading Bot

GrokTrade is a professional-grade autonomous trading system that leverages **xAI's Grok 4.1 (Fast Reasoning)** to execute trades on the Alpaca markets. Unlike basic "chatbots," GrokTrade implements a full "Plan-Measure-Execute" quantitative architecture with code-enforced risk management and persistent cloud memory.

---

## 🚀 Key Features

### 🧠 Grok 4.1 Intelligence
- **Iterative Reasoning**: Every 10 minutes, Grok enters a 10-turn tool-calling loop to scan markets, analyze indicators, and calculate risk.
- **Plan-Before-Execute**: Grok is instructed to verify data, calculate volatility-adjusted sizing, and save a "Thesis Card" before placing any trade.

### 🛡️ Professional Risk Engine
- **Hard Constraints**: Trades are strictly limited between **$5,000 - $25,000** notional.
- **Exposure Caps**: No single ticker can exceed **20%** of the total portfolio value.
- **Wash-Sale Prevention**: A **30-minute cooldown** is enforced after selling a ticker before it can be re-entered.
- **Frequency Limit**: Maximum of **3 trades per cycle** to prevent AI churn.

### 🦅 Bionic Vision (Quantitative Tools)
- **ATR-Based Sizing**: A dedicated tool (`calculate_risk_size`) computes share counts based on Average True Range and portfolio risk-of-ruin math.
- **Market Screener**: Real-time "Market Movers" scanning across a curated **Candidate Universe** (Tech leaders, Sector ETFs, Crypto proxies).
- **Multi-Timeframe Analysis**: Indicators support 15m, 1h, and 1D context.

### 💾 Persistent Cloud Memory (Supabase)
- **Trade Journal**: Every trade is logged with the AI's specific reasoning in the `trade_journal` table.
- **Thesis Cards**: Strategic plans (Entry, Stop, Target) are persisted in the `position_thesis` table.
- **Shared Notes**: A "global brain" for strategy adjustments that persists across restarts.
- **Cloud Telemetry**: Asynchronous logging of bot activity to the `bot_logs` table for remote monitoring.

---

## 📁 Repository Structure

```text
├── src/
│   ├── agent/         # Grok-4 Client and LLM Logic
│   ├── analysis/      # Indicators, Journaling, Notes, and Thesis Management
│   ├── data/          # Alpaca Market Data and Web Search (DuckDuckGo)
│   ├── portfolio/     # Alpaca Portfolio and Trade Execution
│   ├── risk/          # THE RISK ENGINE (Validation Layer)
│   └── live_main.py   # Main Deployment Entry Point
├── deploy.sh          # VM Deployment Script
└── grok_trading.service # Systemd Configuration for 24/7 Uptime
```

---

## 🛠️ Setup & Installation

### 1. Requirements
- Python 3.10+
- Alpaca Paper Trading Account
- xAI (Grok) API Key
- Supabase Project (for persistence)

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root:
```env
# Alpaca
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
APCA_API_BASE_URL=https://paper-api.alpaca.markets

# xAI
XAI_API_KEY=your_grok_key

# Supabase
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

### 4. Database Setup
Ensure the following tables exist in your Supabase project:
- `trade_journal` (ticker, action, shares, price, reason)
- `trading_notes` (content, updated_at)
- `bot_logs` (timestamp, level, message, meta)
- `position_thesis` (ticker, thesis, invalidation_price, target_price, is_active)

---

## 🏃 Running the Bot

### Locally
```bash
python src/live_main.py
```

### Production (systemd)
```bash
sudo cp grok_trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable grok_trading
sudo systemctl start grok_trading
```

---

## 📜 Disclaimer
*This bot is for educational/paper trading purposes. Use in live markets at your own risk. Past AI performance is not indicative of future results.*
# grok-trading-backend
