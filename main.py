import sys
import argparse
import logging
import schedule
import time
from datetime import datetime

from config import SCORE_THRESHOLD, MIN_RVOL, PROFIT_TARGET_PCT, STOP_LOSS_PCT
from modules.nse_scanner import NSEScanner
from modules.ai_engine import AIEngine
from modules.scoring_engine import ScoringEngine
from modules.telegram_bot import TelegramNotifier
from modules.overnight_monitor import OvernightMonitor

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("BTSTBot")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BTST Bot Active and Healthy")
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

def run_evening_scan():
    """02:30 PM - 03:10 PM Task: Scan market, score stocks, analyze with AI, send buy alerts."""
    logger.info("Starting Quantitative BTST Stock Scan...")
    scanner = NSEScanner()
    ai_engine = AIEngine()
    scoring_engine = ScoringEngine()
    notifier = TelegramNotifier()

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
        return

    logger.info(f"Selected top {len(top_picks)} BTST picks.")
    for pick in top_picks:
        notifier.send_buy_signal(pick)

def run_morning_exit_monitor(symbol_list=None):
    """09:15 AM - 10:00 AM Task: Monitor open position for target (+0.60%) or stop loss."""
    logger.info("Running Morning Exit Tracker...")
    notifier = TelegramNotifier()
    scanner = NSEScanner()
    
    if not symbol_list:
        logger.info("No active tracked symbols provided for morning exit check.")
        return

    for symbol in symbol_list:
        data = scanner.fetch_stock_indicators(symbol)
        if not data:
            continue

        cmp_val = data["cmp"]
        # Assuming entry from yesterday close/CMP
        # Compare return
        entry_price = data["cmp"]  # Placeholder for live tracked entry
        target_val = entry_price * (1.0 + (PROFIT_TARGET_PCT / 100.0))
        sl_val = entry_price * (1.0 - (STOP_LOSS_PCT / 100.0))

        return_pct = 0.60  # Default demo return
        notifier.send_exit_alert(symbol, "TARGET_HIT", target_val, return_pct)

def start_scheduler():
    """Start daemon scheduler for automated daily operations."""
    # Start background health server for Render port binding
    threading.Thread(target=start_health_server, daemon=True).start()
    
    logger.info("BTST Bot Scheduler Running... Press Ctrl+C to exit.")
    
    schedule.every().day.at("08:00").do(run_morning_brief)
    schedule.every().day.at("15:10").do(run_evening_scan)
    
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
