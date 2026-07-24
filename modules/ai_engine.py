import requests
import json
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import AI_PROVIDER, AI_API_KEY

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self, provider: str = None, api_key: str = None):
        self.provider = (provider or AI_PROVIDER).lower()
        self.api_key = api_key or AI_API_KEY

    def analyze_stock(self, stock_metrics: dict) -> dict:
        """Analyze a candidate stock and return a sentiment score (0-100) and brief rationale."""
        symbol = stock_metrics['symbol'].replace('.NS', '')
        cmp_val = stock_metrics['cmp']
        rvol = stock_metrics['rvol']
        dist_52w = stock_metrics['dist_from_52w_high_pct']

        if not self.api_key or self.api_key.startswith("your_"):
            logger.info("No AI API key found. Using quantitative fallback rationale.")
            return self._fallback_analysis(stock_metrics)

        prompt = (
            f"You are a professional Indian equity quantitative analyst evaluating a BTST (Buy Today Sell Tomorrow) stock.\n"
            f"Stock Symbol: {symbol}\n"
            f"Current Price: ₹{cmp_val:.2f}\n"
            f"Volume Spike (RVOL): {rvol:.2f}x average 20-day volume\n"
            f"Distance from 52-Week High: {dist_52w:.2f}%\n"
            f"Target: +0.60% profit next morning.\n\n"
            f"Respond ONLY in valid JSON format with keys:\n"
            f'{{"sentiment_score": <number 0 to 100>, "rationale": "<2-sentence technical rationale>"}}'
        )

        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt)
            elif self.provider == "openai":
                return self._call_openai(prompt)
            elif self.provider == "deepseek":
                return self._call_deepseek(prompt)
            else:
                return self._fallback_analysis(stock_metrics)
        except Exception as e:
            logger.error(f"AI API request failed ({self.provider}): {e}")
            return self._fallback_analysis(stock_metrics)

    def _call_gemini(self, prompt: str) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        proxies = None
        if "PYTHONANYWHERE_DOMAIN" in os.environ or "http_proxy" in os.environ or "HTTP_PROXY" in os.environ or os.path.exists("/etc/pythonanywhere"):
            proxies = {
                "http": "http://proxy.server:3128",
                "https": "http://proxy.server:3128"
            }
        session = requests.Session()
        if proxies:
            session.trust_env = False
        res = session.post(url, json=payload, proxies=proxies, timeout=15)
        data = res.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        return self._parse_json_response(text)

    def _call_openai(self, prompt: str) -> dict:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        data = res.json()
        text = data['choices'][0]['message']['content']
        return self._parse_json_response(text)

    def _call_deepseek(self, prompt: str) -> dict:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        data = res.json()
        text = data['choices'][0]['message']['content']
        return self._parse_json_response(text)

    def _parse_json_response(self, text: str) -> dict:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return {
            "sentiment_score": float(data.get("sentiment_score", 75)),
            "rationale": str(data.get("rationale", "Strong volume breakout setup."))
        }

    def ask_ai(self, question: str) -> str:
        """Answer general financial market questions."""
        if not self.api_key or self.api_key.startswith("your_"):
            return "❌ Gemini API key not configured."

        system_instruction = (
            "You are a professional Indian Stock Market analyst and financial assistant. "
            "Provide a helpful, concise, and technically accurate answer to the user's question. "
            "Keep the response under 150 words and use clean HTML formatting (like <b>bold</b>, <i>italic</i>, <code>code</code>, or newlines). "
            "Do NOT use markdown characters like ** or ```."
        )
        prompt = f"{system_instruction}\n\nUser Question: {question}"

        try:
            if self.provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                proxies = None
                if "PYTHONANYWHERE_DOMAIN" in os.environ or "http_proxy" in os.environ or "HTTP_PROXY" in os.environ or os.path.exists("/etc/pythonanywhere"):
                    proxies = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"}
                session = requests.Session()
                if proxies:
                    session.trust_env = False
                res = session.post(url, json=payload, proxies=proxies, timeout=15)
                data = res.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                    return text
                else:
                    logger.error(f"Gemini API error response: {data}")
                    err_msg = data.get("error", {}).get("message", "Unknown error")
                    return f"❌ Gemini API Error: {err_msg}"
            else:
                return "❌ Chat feature currently only configured for Gemini provider."
        except Exception as e:
            logger.error(f"Failed to fetch response from Gemini: {e}")
            return f"❌ Error contacting Gemini: {e}"

    def _fallback_analysis(self, stock_metrics: dict) -> dict:
        symbol = stock_metrics['symbol'].replace('.NS', '')
        rvol = stock_metrics['rvol']
        return {
            "sentiment_score": 80.0 if rvol >= 2.5 else 70.0,
            "rationale": f"{symbol} exhibits strong intraday volume expansion ({rvol:.1f}x) and positive momentum alignment for BTST target (+0.60%)."
        }

if __name__ == "__main__":
    ai = AIEngine()
    sample_stock = {"symbol": "TCS.NS", "cmp": 3900.0, "rvol": 2.6, "dist_from_52w_high_pct": 1.2}
    print(ai.analyze_stock(sample_stock))
