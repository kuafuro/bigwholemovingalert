# ==================== ai_analyst.py V22 ====================
# Engine 4: AI 8-K Filing Analyzer
# Upgrade: Gemini 3.1 Pro + Supabase + Finnhub + Ticker
# ============================================================
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import os, re, json
from google import genai
from google.genai import types

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    print("Gemini 3.1 Pro ready")

def supabase_insert(data):
    if not SUPABASE_URL or not SUPABASE_KEY: return False
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/whale_alerts", headers=headers, json=data)
        return resp.status_code == 201
    except: return False

def supabase_link_exists(link):
    if not SUPABASE_URL or not SUPABASE_KEY: return False
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/whale_alerts?sec_link=eq.{link}&select=id&limit=1", headers=headers)
        return resp.status_code == 200 and len(resp.json()) > 0
    except: return False

def get_stock_quote(ticker):
    if not FINNHUB_API_KEY or ticker == "N/A": return "N/A", "N/A", 0, 0
    try:
        resp = requests.get(f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}")
        if resp.status_code == 200:
            d = resp.json()
            p, c = d.get('c',0), d.get('dp',0)
            if p and p > 0:
                s = "+" if c > 0 else ""
                i = "\U0001f7e2" if c > 0 else ("\U0001f534" if c < 0 else "\u26aa")
                return f"${p:.2f}", f"{i} {s}{c:.2f}%", p, c
    except: pass
    return "N/A", "N/A", 0, 0

def extract_ticker(txt):
    m = re.search(r'<(?:issuerTradingSymbol|tradingSymbol)>\s*([^<]+?)\s*</', txt, re.IGNORECASE)
    if m: return m.group(1).strip().upper()
    m = re.search(r'TICKER SYMBOL:\s*([^\n\r]+)', txt[:5000])
    if m: return m.group(1).strip().upper()
    return "N/A"

def send_telegram(msg):
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", params={'chat_id': CHAT_ID_WHALE, 'text': msg, 'parse_mode': 'HTML'})

hdrs = {'User-Agent': 'WhaleRadarBot Admin@kuafuorhk.com'}
now_utc = datetime.now(timezone.utc)
time_limit = now_utc - timedelta(minutes=15)

try:
    resp = requests.get('https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=only&count=40&output=atom', headers=hdrs)
    soup = BeautifulSoup(resp.content, 'xml')
    entries = soup.find_all('entry')
    print(f"Found {len(entries)} 8-K entries")
    found = 0

    for entry in entries:
        try:
            if datetime.fromisoformat(entry.updated.text.replace('Z','+00:00')).astimezone(timezone.utc) < time_limit: break
        except: continue

        link = entry.link['href']
        if supabase_link_exists(link): continue
        if not gemini_client: break

        company = entry.title.text.split(' - ')[0].strip() if entry.title else "Unknown"
        txt_resp = requests.get(link.replace('-index.htm','.txt'), headers=hdrs)

        if txt_resp.status_code == 200:
            content = txt_resp.text
            ticker = extract_ticker(content)
            price_str, change_str, cur_price, chg_pct = get_stock_quote(ticker)

            prompt = (
                "This is a partial US SEC 8-K filing. Act as a professional Wall Street analyst. "
                "Summarize the key points in Traditional Chinese in 3-5 sentences. "
                "Judge if bullish, bearish, or neutral. Use emoji: \U0001f680 bullish, \U0001f4c9 bearish, \U0001f610 neutral.\n\n"
                f"Filing:\n{content[:15000]}"
            )
            try:
                ai_resp = gemini_client.models.generate_content(model="gemini-3.1-pro-preview", contents=prompt)
                summary = ai_resp.text.strip()
                sentiment = "bullish" if "\U0001f680" in summary else ("bearish" if "\U0001f4c9" in summary else "neutral")

                msg = "\U0001f916 <b>\u3010AI 8-K \u8ca1\u5831\u79d2\u8b80\u6a5f\u3011</b>\n"
                msg += f"\U0001f3e2 \u516c\u53f8: <b>{company} ({ticker})</b>\n"
                if ticker != "N/A": msg += f"\U0001f4b2 \u80a1\u50f9: <b>{price_str}</b>  {change_str}\n"
                msg += f"\U0001f4dd <b>AI \u7e3d\u7d50:</b>\n{summary}\n\n"
                msg += f"\U0001f517 <a href='{link}'>\u67e5\u770b 8-K \u539f\u6587</a>"

                send_telegram(msg)
                print(f"  Sent: {company} ({ticker})")
                supabase_insert({"source":"8k","ticker":ticker,"company_name":company,"action":"8-K","price":cur_price,"change_pct":chg_pct,"ai_summary":summary,"sentiment":sentiment,"sec_link":link})
                found += 1
                time.sleep(2)
            except Exception as e: print(f"AI error: {e}")
        if found >= 3: break
except Exception as e: print(f"8-K engine error: {e}")
