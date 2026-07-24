import sys
import argparse
import logging
import schedule
import time
import os
from datetime import datetime

from datetime import datetime, timedelta, timezone

# India Time (IST) is UTC + 5:30. Let's make logs print in IST.
def ist_time_converter(*args):
    utc_dt = datetime.now(timezone.utc)
    ist_dt = utc_dt + timedelta(hours=5, minutes=30)
    return ist_dt.timetuple()

logging.Formatter.converter = ist_time_converter

from config import SCORE_THRESHOLD, MIN_RVOL, PROFIT_TARGET_PCT, STOP_LOSS_PCT
from modules.nse_scanner import NSEScanner
from modules.ai_engine import AIEngine
from modules.scoring_engine import ScoringEngine
from modules.telegram_bot import TelegramNotifier
from modules.overnight_monitor import OvernightMonitor

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

LOG_BUFFER = []

class ListLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        LOG_BUFFER.append(log_entry)
        if len(LOG_BUFFER) > 100:
            LOG_BUFFER.pop(0)

# Configure Logging
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)
list_handler = ListLogHandler()
list_handler.setFormatter(log_formatter)

logger = logging.getLogger("BTSTBot")
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler)
logger.addHandler(list_handler)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/logs":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            log_content = "\n".join(LOG_BUFFER)
            self.wfile.write(log_content.encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"BTST Bot Active and Healthy")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
        
    def do_POST(self):
        if self.path == "/telegram-webhook":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.send_response(200)
            self.end_headers()
            
            try:
                update = json.loads(post_data.decode("utf-8"))
                message = update.get("message", {})
                text = message.get("text", "").strip()
                chat_id = message.get("chat", {}).get("id")
                
                # Check for /buy or /entry command
                if text.lower().startswith(("/buy", "/entry")) and chat_id:
                    parts = text.split()
                    if len(parts) >= 3:
                        symbol = parts[1].upper()
                        if not symbol.endswith(".NS"):
                            symbol += ".NS"
                        try:
                            custom_entry = float(parts[2])
                            self.handle_custom_entry_command(symbol, custom_entry)
                        except ValueError:
                            notifier = TelegramNotifier()
                            notifier.send_message("❌ <b>Invalid format.</b> Use: <code>/buy JSWSTEEL 1265.50</code>")
                    else:
                        notifier = TelegramNotifier()
                        notifier.send_message("❌ <b>Invalid format.</b> Use: <code>/buy JSWSTEEL 1265.50</code>")
            except Exception as e:
                logger.error(f"Error handling Telegram webhook POST: {e}")
        else:
            self.send_response(404)
            self.end_headers()

    def handle_custom_entry_command(self, symbol: str, entry_price: float):
        """Update active trade with custom entry price and recalculate targets."""
        notifier = TelegramNotifier()
        active_trades = load_active_trades()
        found = False
        
        for trade in active_trades:
            if trade["symbol"].upper() == symbol:
                trade["cmp"] = entry_price
                # Recalculate +0.60% Target and -1.50% Stop Loss
                trade["target_price"] = round(entry_price * (1.0 + (PROFIT_TARGET_PCT / 100.0)), 2)
                trade["stop_loss_price"] = round(entry_price * (1.0 - (STOP_LOSS_PCT / 100.0)), 2)
                found = True
                break
                
        if found:
            save_active_trades(active_trades)
            clean_symbol = symbol.replace(".NS", "")
            target = next(t["target_price"] for t in active_trades if t["symbol"] == symbol)
            sl = next(t["stop_loss_price"] for t in active_trades if t["symbol"] == symbol)
            
            msg = (
                f"✅ <b>Entry Updated for {clean_symbol}</b>\n\n"
                f"• Actual Entry: ₹{entry_price:.2f}\n"
                f"• Target (+0.60%): 🎯 <b>₹{target:.2f}</b>\n"
                f"• Stop Loss (-1.50%): 🛡️ <b>₹{sl:.2f}</b>\n\n"
                f"<i>Exit alerts will now trigger at these updated levels.</i>"
            )
            notifier.send_message(msg)
        else:
            clean_symbol = symbol.replace(".NS", "")
            notifier.send_message(f"❌ <b>Stock {clean_symbol} not found</b> in yesterday's active BTST list.")

    def log_message(self, format, *args):
        return  # Suppress HTTP access logs

def start_health_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health check HTTP server listening on port {port}")
    server.serve_forever()

def run_morning_brief():
    """08:00 AM Task: Send pre-market overview to Telegram."""
    logger.info("Executing 08:00 AM Morning Market Brief...")
    monitor = OvernightMonitor()
    notifier = TelegramNotifier()
    
    gift_status = monitor.get_gift_nifty_status()
    global_cues = monitor.get_global_cues()
    notifier.send_morning_brief(gift_status, global_cues)

import json

ACTIVE_TRADES_FILE = "active_trades.json"

def save_active_trades(trades):
    try:
        with open(ACTIVE_TRADES_FILE, "w") as f:
            json.dump(trades, f, indent=2)
        logger.info(f"Saved {len(trades)} active trades to {ACTIVE_TRADES_FILE}")
    except Exception as e:
        logger.error(f"Error saving active trades: {e}")

def load_active_trades():
    try:
        if os.path.exists(ACTIVE_TRADES_FILE):
            with open(ACTIVE_TRADES_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading active trades: {e}")
    return []

def run_evening_scan():
    """02:30 PM - 03:10 PM Task: Scan market, score stocks, analyze with AI, send buy alerts."""
    logger.info("Starting Quantitative BTST Stock Scan...")
    scanner = NSEScanner()
    ai_engine = AIEngine()
    scoring_engine = ScoringEngine()
    notifier = TelegramNotifier()

    # Check for NSE Market Holiday
    if scanner.is_market_holiday():
        logger.info("Today is an official NSE Trading Holiday. Skipping scan.")
        notifier.send_message("🏖️ <b>NSE Market Holiday:</b> Indian stock market is closed today for a trading holiday. Enjoy your day!")
        return

    # 1. Fetch market data
    all_stocks = scanner.scan_market()
    if not all_stocks:
        logger.warning("No stock data returned from scanner.")
        return

    # 2. Pre-filter candidates by RVOL and distance from 52W High
    candidates = [
        s for s in all_stocks
        if s["rvol"] >= MIN_RVOL and s["dist_from_52w_high_pct"] <= 5.0
    ]

    logger.info(f"Filtered {len(candidates)} candidates matching quantitative baseline (RVOL >= {MIN_RVOL}x).")

    scored_picks = []
    for stock in candidates:
        # 3. AI Analysis
        ai_res = ai_engine.analyze_stock(stock)
        # 4. Compute Final Trade Quality Score
        evaluated = scoring_engine.evaluate_stock(stock, ai_res)
        if evaluated["score"] >= SCORE_THRESHOLD:
            scored_picks.append(evaluated)

    # Sort picks by score descending
    scored_picks.sort(key=lambda x: x["score"], reverse=True)
    top_picks = scored_picks[:2]  # Pick top 1-2 high conviction stocks

    if not top_picks:
        logger.info("No candidates passed the high-conviction quality score threshold today.")
        notifier.send_message("ℹ️ <b>BTST Scan Complete:</b> No stocks met the strict 70+ quality score threshold today.")
        save_active_trades([])
        return

    logger.info(f"Selected top {len(top_picks)} BTST picks.")
    save_active_trades(top_picks)
    for pick in top_picks:
        notifier.send_buy_signal(pick)

def run_morning_exit_monitor():
    """09:15 AM - 10:00 AM Task: Monitor open position for target (+0.60%) or stop loss."""
    logger.info("Running Morning Exit Tracker...")
    notifier = TelegramNotifier()
    scanner = NSEScanner()
    
    active_trades = load_active_trades()
    if not active_trades:
        logger.info("No active tracked trades from yesterday.")
        return

    for trade in active_trades:
        symbol = trade["symbol"]
        entry_price = trade["cmp"]
        target_price = trade["target_price"]
        sl_price = trade["stop_loss_price"]

        data = scanner.fetch_stock_indicators(symbol)
        if not data:
            continue

        cmp_val = data["cmp"]
        return_pct = ((cmp_val - entry_price) / entry_price) * 100.0

        if cmp_val >= target_price:
            notifier.send_exit_alert(symbol, "TARGET_HIT", cmp_val, return_pct)
        elif cmp_val <= sl_price:
            notifier.send_exit_alert(symbol, "STOP_LOSS", cmp_val, return_pct)
        else:
            notifier.send_exit_alert(symbol, "TIME_EXIT", cmp_val, return_pct)

    # Reset active trades after morning check
    save_active_trades([])

def register_telegram_webhook():
    """Register Render server URL with Telegram API for webhooks."""
    time.sleep(5)  # Wait for server to boot
    from config import TELEGRAM_BOT_TOKEN
    if TELEGRAM_BOT_TOKEN and not TELEGRAM_BOT_TOKEN.startswith("your_"):
        webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url=https://btst-bot.onrender.com/telegram-webhook"
        try:
            import requests
            res = requests.get(webhook_url, timeout=10)
            logger.info(f"Telegram webhook registration response: {res.json()}")
        except Exception as e:
            logger.error(f"Error registering Telegram webhook: {e}")

def start_scheduler():
    """Start daemon scheduler for automated daily operations."""
    # Start background health server for Render port binding
    threading.Thread(target=start_health_server, daemon=True).start()
    
    # Register Telegram Webhook in background
    threading.Thread(target=register_telegram_webhook, daemon=True).start()
    
    logger.info("BTST Bot Scheduler Running... Press Ctrl+C to exit.")
    
    schedule.every().day.at("02:30").do(run_morning_brief)       # 08:00 AM IST
    schedule.every().day.at("03:45").do(run_morning_exit_monitor) # 09:15 AM IST
    schedule.every().day.at("09:40").do(run_evening_scan)          # 03:10 PM IST
    
    while True:
        schedule.run_pending()
        time.sleep(30)

def main():
    parser = argparse.ArgumentParser(description="Automated BTST Stock Recommendation & Alert Bot")
    parser.add_argument("--scan", action="store_true", help="Run 03:10 PM evening stock scan immediately")
    parser.add_argument("--morning", action="store_true", help="Run 08:00 AM morning market brief immediately")
    parser.add_argument("--monitor-exit", action="store_true", help="Run 09:15 AM exit tracking check immediately")
    parser.add_argument("--schedule", action="store_true", help="Start continuous daily scheduler daemon")

    args = parser.parse_args()

    if args.scan:
        run_evening_scan()
    elif args.morning:
        run_morning_brief()
    elif args.monitor_exit:
        run_morning_exit_monitor()
    elif args.schedule:
        start_scheduler()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
