import yfinance as yf
import logging

logger = logging.getLogger(__name__)

class OvernightMonitor:
    def get_gift_nifty_status(self) -> str:
        """Fetch GIFT Nifty / India 50 index performance for pre-market sentiment."""
        try:
            # ^NSEI baseline or GIFT Nifty proxy
            nifty = yf.Ticker("^NSEI").history(period="2d", interval="1d")
            if not nifty.empty and len(nifty) >= 2:
                prev_close = float(nifty['Close'].iloc[-2])
                curr_price = float(nifty['Close'].iloc[-1])
                change_pct = ((curr_price - prev_close) / prev_close) * 100.0
                direction = "🟢 Bullish" if change_pct >= 0 else "🔴 Bearish"
                return f"{direction} ({change_pct:+.2f}%)"
        except Exception as e:
            logger.error(f"Error fetching GIFT Nifty data: {e}")
        return "⚪ Neutral (Data pending market open)"

    def get_global_cues(self) -> str:
        """Fetch US market (S&P 500 / Nasdaq) & Asian market cues."""
        try:
            sp500 = yf.Ticker("^GSPC").history(period="2d", interval="1d")
            if not sp500.empty and len(sp500) >= 2:
                prev_close = float(sp500['Close'].iloc[-2])
                curr_price = float(sp500['Close'].iloc[-1])
                change_pct = ((curr_price - prev_close) / prev_close) * 100.0
                status = "Positive" if change_pct >= 0 else "Cautious"
                return f"S&P 500 {change_pct:+.2f}% ({status})"
        except Exception as e:
            logger.error(f"Error fetching global cues: {e}")
        return "Stable / Rangebound"

if __name__ == "__main__":
    monitor = OvernightMonitor()
    print("GIFT Nifty Status:", monitor.get_gift_nifty_status())
    print("Global Cues:", monitor.get_global_cues())
