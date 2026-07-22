import urllib.request
import json
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send formatted notification via Telegram Bot API."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram Bot Token or Chat ID not configured. Printing message to console:")
            print("\n--- TELEGRAM NOTIFICATION ---")
            print(text)
            print("------------------------------\n")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))

            if res_json.get("ok"):
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {res_json}")
                return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def send_morning_brief(self, gift_nifty_status: str, global_cues: str):
        """Send 08:00 AM Morning Market Alert."""
        msg = (
            "<b>☀️ BTST BOT — MORNING MARKET BRIEF (08:00 AM)</b>\n\n"
            f"📈 <b>GIFT Nifty Status:</b> {gift_nifty_status}\n"
            f"🌍 <b>Global Market Cues:</b> {global_cues}\n\n"
            "<i>Bot status: Active. Evening stock scan scheduled for 02:30 PM.</i>"
        )
        return self.send_message(msg)

    def send_buy_signal(self, stock_data: dict):
        """Send 03:10 PM BTST Recommendation Alert."""
        symbol = stock_data["symbol"].replace(".NS", "")
        cmp_price = stock_data["cmp"]
        target_price = stock_data["target_price"]
        sl_price = stock_data["stop_loss_price"]
        shares = stock_data["rec_shares"]
        capital = stock_data["rec_capital"]
        score = stock_data["score"]
        rvol = stock_data["rvol"]
        ai_summary = stock_data.get("ai_summary", "High momentum breakout signal.")

        msg = (
            f"<b>🚀 BTST BUY ALERT — HIGH CONVICTION</b>\n\n"
            f"<b>Stock:</b> <code>{symbol}</code>\n"
            f"<b>Entry Price (CMP):</b> ₹{cmp_price:.2f}\n"
            f"<b>Target (+0.60%):</b> 🎯 <b>₹{target_price:.2f}</b>\n"
            f"<b>Stop Loss (-1.50%):</b> 🛡️ <b>₹{sl_price:.2f}</b>\n\n"
            f"📊 <b>Quantitative Metrics:</b>\n"
            f"• Quality Score: {score:.1f} / 100\n"
            f"• Volume Spike: {rvol:.1f}x Average Volume\n\n"
            f"💰 <b>Recommended Allocation:</b>\n"
            f"• Quantity: {shares} shares (~₹{capital:.0f})\n\n"
            f"🧠 <b>AI Sentiment:</b>\n"
            f"<i>\"{ai_summary}\"</i>\n\n"
            f"⚠️ <i>Manual Execution: Buy on your broker app before 03:25 PM closing.</i>"
        )
        return self.send_message(msg)

    def send_exit_alert(self, symbol: str, alert_type: str, price: float, return_pct: float):
        """Send Morning Exit Tracking Alert."""
        symbol = symbol.replace(".NS", "")
        if alert_type == "TARGET_HIT":
            header = "✅ <b>TARGET ACHIEVED (+0.60% PROFIT BOOKED)</b>"
            action = "Target reached! Consider selling manually now."
        elif alert_type == "STOP_LOSS":
            header = "❌ <b>STOP LOSS TRIGGERED</b>"
            action = "Stop loss hit. Consider exiting position."
        else:
            header = "⏰ <b>10:00 AM TIME EXIT ALERT</b>"
            action = "Holding time limit reached. Consider closing position to free up capital."

        msg = (
            f"{header}\n\n"
            f"<b>Stock:</b> <code>{symbol}</code>\n"
            f"<b>Current Price:</b> ₹{price:.2f}\n"
            f"<b>P&L Return:</b> {return_pct:+.2f}%\n\n"
            f"💡 <i>Action Required: {action}</i>"
        )
        return self.send_message(msg)

if __name__ == "__main__":
    notifier = TelegramNotifier()
    print("Testing Telegram Notifier Output...")
    notifier.send_buy_signal({
        "symbol": "RELIANCE.NS",
        "cmp": 2950.0,
        "target_price": 2967.70,
        "stop_loss_price": 2905.75,
        "rec_shares": 3,
        "rec_capital": 8850.0,
        "score": 85.5,
        "rvol": 2.4,
        "ai_summary": "Strong institutional volume breakout near 52-week high with positive sector momentum."
    })
