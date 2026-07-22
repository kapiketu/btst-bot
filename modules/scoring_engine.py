import logging
from config import PROFIT_TARGET_PCT, STOP_LOSS_PCT, MAX_CAPITAL_PER_TRADE

logger = logging.getLogger(__name__)

class ScoringEngine:
    def __init__(self, target_pct: float = None, sl_pct: float = None, max_capital: float = None):
        self.target_pct = target_pct or PROFIT_TARGET_PCT
        self.sl_pct = sl_pct or STOP_LOSS_PCT
        self.max_capital = max_capital or MAX_CAPITAL_PER_TRADE

    def evaluate_stock(self, metrics: dict, ai_analysis: dict) -> dict:
        """Compute Quantitative Trade Quality Score (0-100) and trade setup levels."""
        cmp_val = metrics["cmp"]
        rvol = metrics["rvol"]
        dist_52w = metrics["dist_from_52w_high_pct"]
        rel_strength = metrics["relative_strength"]
        ema20 = metrics["ema20"]
        ema50 = metrics["ema50"]
        ai_score = ai_analysis.get("sentiment_score", 75.0)

        # 1. Volume Spike Score (Max 25 pts)
        vol_score = min(25.0, (rvol / 3.0) * 25.0)

        # 2. Relative Strength Score (Max 20 pts)
        rs_score = 20.0 if rel_strength >= 3.0 else max(0.0, (rel_strength / 3.0) * 20.0)

        # 3. 52-Week High Proximity Score (Max 20 pts)
        high_score = max(0.0, 20.0 - (dist_52w * 2.0))

        # 4. EMA Trend Alignment Score (Max 15 pts)
        trend_score = 0.0
        if cmp_val > ema20 > ema50:
            trend_score = 15.0
        elif cmp_val > ema20:
            trend_score = 10.0

        # 5. AI Sentiment Score (Max 20 pts)
        ai_weighted_score = (ai_score / 100.0) * 20.0

        total_score = vol_score + rs_score + high_score + trend_score + ai_weighted_score

        # Price Levels (+0.60% Target, -1.50% Stop Loss)
        target_price = round(cmp_val * (1.0 + (self.target_pct / 100.0)), 2)
        stop_loss_price = round(cmp_val * (1.0 - (self.sl_pct / 100.0)), 2)

        # Position Sizing
        rec_shares = max(1, int(self.max_capital / cmp_val))
        rec_capital = rec_shares * cmp_val

        return {
            **metrics,
            "score": round(total_score, 1),
            "target_price": target_price,
            "stop_loss_price": stop_loss_price,
            "rec_shares": rec_shares,
            "rec_capital": round(rec_capital, 2),
            "ai_summary": ai_analysis.get("rationale", "Momentum breakout setup.")
        }

if __name__ == "__main__":
    engine = ScoringEngine()
    dummy_metrics = {
        "symbol": "INFY.NS",
        "cmp": 1600.0,
        "rvol": 2.5,
        "dist_from_52w_high_pct": 1.5,
        "relative_strength": 2.5,
        "ema20": 1580.0,
        "ema50": 1550.0
    }
    dummy_ai = {"sentiment_score": 85.0, "rationale": "Solid volume breakout above key resistance."}
    res = engine.evaluate_stock(dummy_metrics, dummy_ai)
    print(f"Total Quality Score: {res['score']} | Target: ₹{res['target_price']} | SL: ₹{res['stop_loss_price']}")
