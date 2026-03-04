import os
import requests

FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')


def get_stock_quote(ticker):
    if not FINNHUB_API_KEY or ticker == "N/A":
        return "N/A", "N/A", 0, 0
    try:
        resp = requests.get(f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}")
        if resp.status_code == 200:
            d = resp.json()
            price, change = d.get('c', 0), d.get('dp', 0)
            if price and price > 0:
                sign = "+" if change > 0 else ""
                icon = "\U0001f7e2" if change > 0 else ("\U0001f534" if change < 0 else "\u26aa")
                return f"${price:.2f}", f"{icon} {sign}{change:.2f}%", price, change
    except Exception as e:
        print(f"  ⚠️ Finnhub error: {e}")
    return "N/A", "N/A", 0, 0


def get_company_profile(ticker):
    if not FINNHUB_API_KEY or ticker == "N/A":
        return {"sector": "N/A", "industry": "N/A", "marketCap": 0}
    try:
        resp = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={FINNHUB_API_KEY}")
        if resp.status_code == 200:
            d = resp.json()
            return {
                "sector": d.get('finnhubIndustry', 'N/A'),
                "industry": d.get('finnhubIndustry', 'N/A'),
                "marketCap": d.get('marketCapitalization', 0)
            }
    except Exception as e:
        print(f"  ⚠️ Finnhub profile error: {e}")
    return {"sector": "N/A", "industry": "N/A", "marketCap": 0}
