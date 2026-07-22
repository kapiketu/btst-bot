# 🚀 Automated BTST Stock Recommendation & Alert Bot

An institutional-grade quantitative BTST (Buy Today, Sell Tomorrow) recommendation engine and Telegram alert bot for Indian Equities (NSE).

---

## 🌟 Key Features

1. **Quantitative Scanner**: Automatically scans Nifty liquid stocks for volume spikes (RVOL 2x-3x), 52-week high momentum, 20/50 EMA trends, and relative strength vs Nifty 50.
2. **AI Sentiment Integration**: Seamlessly integrates with **Gemini**, **OpenAI (GPT-4o)**, or **DeepSeek** to provide sentiment scoring and 2-sentence rationale.
3. **Trade Quality Scoring Engine**: Scores every candidate on a 0–100 scale; triggers alerts only for high-conviction setups (Score $\ge 70$).
4. **Target & Risk Sizing**: Configured for a minimum **+0.60% profit target** and **-1.50% stop loss**, with automated position sizing calculation based on your defined budget.
5. **Instant Telegram Alerts**: Delivers clean, formatted alerts directly to your phone via Telegram Bot API for manual execution.

---

## 🛠️ Quick Setup Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and enter your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=987654321

AI_PROVIDER=gemini
AI_API_KEY=your_gemini_or_openai_or_deepseek_key_here

PROFIT_TARGET_PCT=0.60
STOP_LOSS_PCT=1.50
MAX_CAPITAL_PER_TRADE=10000
```

> **How to get Telegram Bot Token & Chat ID:**
> 1. Open Telegram and search for `@BotFather`.
> 2. Send `/newbot` to create a bot and copy the **HTTP API Token**.
> 3. Search for `@userinfobot` on Telegram and send any message to copy your **Chat ID**.

---

## 🚦 Usage Commands

### Test 03:10 PM BTST Scanner Immediately
```bash
python main.py --scan
```

### Test 08:00 AM Morning Market Brief
```bash
python main.py --morning
```

### Start Continuous Daily Scheduler Daemon
```bash
python main.py --schedule
```

---

## 📅 Daily Execution Schedule

| Time | Action | Output |
| :--- | :--- | :--- |
| **08:00 AM** | Morning Market Cues | GIFT Nifty & Global overview on Telegram |
| **02:30 – 03:10 PM** | Quantitative Scan & AI Evaluation | Top 1-2 BTST buy signals on Telegram |
| **09:15 – 10:00 AM** | Target & Exit Monitor | Profit target hit (+0.60%) / SL notifications |
