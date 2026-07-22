import yfinance as yf
import pandas as pd
import numpy as np
import logging
from typing import List, Dict
from config import STOCK_UNIVERSE

logger = logging.getLogger(__name__)

from datetime import date

# Official NSE Trading Holidays for 2026
NSE_HOLIDAYS_2026 = {
    "2026-01-26", # Republic Day
    "2026-03-08", # Mahashivratri
    "2026-03-25", # Holi
    "2026-03-29", # Good Friday
    "2026-04-11", # Id-Ul-Fitr
    "2026-04-14", # Dr. Baba Saheb Ambedkar Jayanti
    "2026-04-17", # Shri Ram Navami
    "2026-04-21", # Mahavir Jayanti
    "2026-05-01", # Maharashtra Day
    "2026-06-17", # Bakri Id
    "2026-07-17", # Muharram
    "2026-08-15", # Independence Day
    "2026-10-02", # Mahatma Gandhi Jayanti
    "2026-10-24", # Dussehra
    "2026-11-01", # Diwali Laxmi Pujan
    "2026-11-15", # Gurunanak Jayanti
    "2026-12-25", # Christmas
}

class NSEScanner:
    def __init__(self, stock_list: List[str] = None):
        self.stock_list = stock_list or STOCK_UNIVERSE

    def is_market_holiday(self) -> bool:
        """Check if today is an official NSE trading holiday."""
        today_str = date.today().strftime("%Y-%m-%d")
        return today_str in NSE_HOLIDAYS_2026

    def fetch_stock_indicators(self, symbol: str) -> Dict:
        """Fetch market data and compute indicators (RVOL, EMA, ATR, 52W High, Relative Strength)."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="60d", interval="1d")

            if df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for {symbol}")
                return None

            current_close = float(df['Close'].iloc[-1])
            current_volume = float(df['Volume'].iloc[-1])
            avg_volume_20 = float(df['Volume'].iloc[-21:-1].mean())

            # Relative Volume (RVOL)
            rvol = (current_volume / avg_volume_20) if avg_volume_20 > 0 else 0.0

            # Moving Averages
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            ema20 = float(df['EMA20'].iloc[-1])
            ema50 = float(df['EMA50'].iloc[-1])

            # 52-Week High Proximity
            high_52w = float(df['High'].max())
            dist_from_52w_high_pct = ((high_52w - current_close) / high_52w) * 100.0

            # ATR (Average True Range) - 14 period
            high_low = df['High'] - df['Low']
            high_cp = np.abs(df['High'] - df['Close'].shift(1))
            low_cp = np.abs(df['Low'] - df['Close'].shift(1))
            tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
            atr14 = float(tr.rolling(14).mean().iloc[-1])

            # 5-Day Stock Return for Relative Strength
            stock_5d_return = ((current_close - float(df['Close'].iloc[-6])) / float(df['Close'].iloc[-6])) * 100.0

            return {
                "symbol": symbol,
                "cmp": current_close,
                "volume": current_volume,
                "avg_vol_20": avg_volume_20,
                "rvol": rvol,
                "ema20": ema20,
                "ema50": ema50,
                "high_52w": high_52w,
                "dist_from_52w_high_pct": dist_from_52w_high_pct,
                "atr14": atr14,
                "stock_5d_return": stock_5d_return
            }

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def fetch_nifty_5d_return(self) -> float:
        """Fetch Nifty 50 5-day performance for Relative Strength baseline."""
        try:
            nifty = yf.Ticker("^NSEI").history(period="10d", interval="1d")
            if not nifty.empty and len(nifty) >= 6:
                close_curr = float(nifty['Close'].iloc[-1])
                close_5d = float(nifty['Close'].iloc[-6])
                return ((close_curr - close_5d) / close_5d) * 100.0
        except Exception as e:
            logger.error(f"Error fetching Nifty 50 index data: {e}")
        return 0.0

    def scan_market(self) -> List[Dict]:
        """Scan the entire universe and return stocks meeting baseline quantitative metrics."""
        nifty_return = self.fetch_nifty_5d_return()
        results = []

        logger.info(f"Scanning {len(self.stock_list)} stocks. Baseline Nifty 5D Return: {nifty_return:+.2f}%")

        for symbol in self.stock_list:
            data = self.fetch_stock_indicators(symbol)
            if data:
                # Relative Strength vs Nifty 50
                data["relative_strength"] = data["stock_5d_return"] - nifty_return
                results.append(data)

        return results

if __name__ == "__main__":
    scanner = NSEScanner(["RELIANCE.NS", "TCS.NS", "ZOMATO.NS"])
    res = scanner.scan_market()
    for r in res:
        print(f"Symbol: {r['symbol']} | CMP: ₹{r['cmp']} | RVOL: {r['rvol']:.2f}x | RS: {r['relative_strength']:+.2f}%")
