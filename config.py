import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# AI Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()  # gemini | openai | deepseek
AI_API_KEY = os.getenv("AI_API_KEY", "")

# Trading Strategy Parameters
PROFIT_TARGET_PCT = float(os.getenv("PROFIT_TARGET_PCT", "0.60"))  # +0.60% Target
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "1.50"))        # -1.50% Stop Loss
MAX_CAPITAL_PER_TRADE = float(os.getenv("MAX_CAPITAL_PER_TRADE", "10000")) # ₹10,000 INR default budget

# Scoring Thresholds
MIN_RVOL = 1.8               # Minimum 1.8x intraday relative volume spike
SCORE_THRESHOLD = 70.0       # Minimum trade quality score out of 100 to trigger alert

# High Liquidity & Momentum Universe (Top NSE Liquid Stocks + Nifty 200 constituents)
STOCK_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "HINDUNILVR.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "TATASTEEL.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "TITAN.NS", "BAJFINANCE.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS", "JSWSTEEL.NS", "HEROMOTOCO.NS",
    "EICHERMOT.NS", "GRASIM.NS", "BPCL.NS", "HCLTECH.NS", "WIPRO.NS",
    "TECHM.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "BAJAJ-AUTO.NS", "DRREDDY.NS",
    "CIPLA.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", "BEL.NS", "HAL.NS",
    "TRENT.NS", "VBL.NS", "JIOFIN.NS", "DLF.NS", "PIDILITIND.NS", "IOC.NS", "GAIL.NS"
]
