# ==================== form144.py V22 ====================
# Engine 2: Form 144 Insider Selling Alert
# Upgrade: Supabase + Finnhub + Gemini 3.1 Pro news search
# =========================================================
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import os
import re
import json
from google import genai
from google.genai import types

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE')
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    print("Gemini 3.1 Pro engine ready")

def supabase_insert(data):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/whale_alerts"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        resp = requests.post(url, headers=headers, json=data)
        return resp.status_code == 201
    except Exception as e:
        print(f"  Supabase error: {e}")
        return False

def supabase_link_exists(link):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/whale_alerts?sec_link=eq.{link}&select=id&limit=1"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        resp = requests.get(url, headers=headers)
        return resp.status_code == 200 and len(resp.json()) > 0
    except:
        return False

def get_stock_quote(ticker):
    if not FINNHUB_API_KEY or ticker == "N/A":
        return "N/A", "N/A", 0, 0
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            price = data.get('c', 0)
            change = data.get('dp', 0)
            if price and price > 0:
                sign = "+" if change > 0 else ""
                icon = "\U0001f7e2" if change > 0 else ("\U0001f534" if change < 0 else "\u26aa")
                return f"${price:.2f}", f"{icon} {sign}{change:.2f}%", price, change
    except:
        pass
    return "N/A", "N/A", 0, 0

def ai_explain_selling(company_name, ticker):
    """Use Gemini 3.1 Pro with Google Search to find news and explain selling"""
    if not gemini_client:
        return "\u26a0\ufe0f \u6709\u5167\u90e8\u4eba\u58eb\u5df2\u63d0\u4ea4\u62cb\u552e\u610f\u5411\u66f8\uff01"
    try:
        prompt = (
            f"You are a Wall Street analyst. The company {company_name} (ticker: {ticker}) "
            f"just had an insider file a Form 144 (intent to sell shares) with the SEC. "
            f"Search for the latest news about this company and explain in Traditional Chinese "
            f"why this insider might be selling. Keep it within 100 words. "
            f"Include relevant recent news, earnings, or events. "
            f"End with a risk assessment emoji: \U0001f534 high risk, \U0001f7e1 medium risk, \U0001f7e2 low risk."
        )
        response = gemini_client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"  Gemini error: {e}")
        return "\u26a0\ufe0f \u6709\u5167\u90e8\u4eba\u58eb\u5df2\u63d0\u4ea4\u62cb\u552e\u610f\u5411\u66f8\uff01"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={'chat_id': CHAT_ID_WHALE, 'text': message, 'parse_mode': 'HTML'})

SEC_HEADERS = {'User-Agent': 'WhaleRadarBot Admin@kuafuorhk.com'}

def get_sec_ticker_map():
    try:
        resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS)
        return {str(v['cik_str']): v['ticker'] for v in resp.json().values()}
    except:
        return {}

CIK_TICKER_MAP = get_sec_ticker_map()
print(f"Loaded {len(CIK_TICKER_MAP)} CIK-Ticker mappings")

url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&owner=only&count=40&output=atom'
now_utc = datetime.now(timezone.utc)
time_limit = now_utc - timedelta(minutes=30)

try:
    response = requests.get(url, headers=SEC_HEADERS)
    soup = BeautifulSoup(response.content, 'xml')
    entries = soup.find_all('entry')
    print(f"Found {len(entries)} Form 144 entries")
    found_count = 0

    for entry in entries:
        updated_tag = entry.find('updated')
        if not updated_tag:
            continue
        try:
            if datetime.fromisoformat(updated_tag.text.replace('Z', '+00:00')).astimezone(timezone.utc) < time_limit:
                break
        except:
            continue

        link = entry.link['href']
        if supabase_link_exists(link):
            continue

        title_text = entry.title.text if entry.title else ""
        txt_link = link.replace('-index.htm', '.txt')
        txt_response = requests.get(txt_link, headers=SEC_HEADERS)

        if txt_response.status_code == 200:
            txt_content = txt_response.text
            ticker = "N/A"
            issuer_name = "\u672a\u77e5\u516c\u53f8"

            # Method 1: XML tags
            sym = re.search(r'<(?:issuerSymbol|issuerTradingSymbol)>\s*([^<]+?)\s*</(?:issuerSymbol|issuerTradingSymbol)>', txt_content, re.IGNORECASE)
            if sym:
                ticker = sym.group(1).strip().upper()
            nm = re.search(r'<(?:nameOfIssuer|issuerName)>\s*([^<]+?)\s*</(?:nameOfIssuer|issuerName)>', txt_content, re.IGNORECASE)
            if nm:
                issuer_name = nm.group(1).strip()

            # Method 2: SGML header
            if ticker == "N/A" or issuer_name == "\u672a\u77e5\u516c\u53f8":
                sgml = re.search(r'(?:SUBJECT COMPANY|ISSUER)[:\s]*(.*?)(?:FILED BY:|REPORTING-OWNER:|<SEC-DOCUMENT>|</SEC-HEADER>|\Z)', txt_content[:5000], re.DOTALL | re.IGNORECASE)
                if sgml:
                    block = sgml.group(1)
                    if issuer_name == "\u672a\u77e5\u516c\u53f8":
                        cn = re.search(r'COMPANY CONFORMED NAME:\s*([^\n\r]+)', block)
                        if cn:
                            issuer_name = cn.group(1).strip()
                    if ticker == "N/A":
                        ck = re.search(r'CENTRAL INDEX KEY:\s*(\d+)', block)
                        if ck:
                            ticker = CIK_TICKER_MAP.get(str(int(ck.group(1).strip())), "N/A")

            # Method 3: Title CIK
            if ticker == "N/A":
                cm = re.search(r'\((\d+)\)\s*\(Subject\)', title_text)
                if cm:
                    ticker = CIK_TICKER_MAP.get(str(int(cm.group(1))), "N/A")

            # Method 4: Title name
            if issuer_name == "\u672a\u77e5\u516c\u53f8":
                tn = re.search(r'144\s*-\s*(.+?)\s*\(\d+\)', title_text)
                if tn:
                    issuer_name = tn.group(1).strip()

            # Method 5: Fallback
            if issuer_name == "\u672a\u77e5\u516c\u53f8":
                alt = re.search(r'COMPANY CONFORMED NAME:\s*([^\n\r]+)', txt_content[:5000])
                if alt:
                    issuer_name = alt.group(1).strip()

            print(f"  {issuer_name} ({ticker})")

            price_str, change_str, current_price, change_pct = get_stock_quote(ticker)
            ai_analysis = ai_explain_selling(issuer_name, ticker)

            msg = "\U0001f6a8 <b>\u3010Form 144 \u5167\u90e8\u9ad8\u7ba1\u9003\u751f\u9810\u8b66\u3011</b>\n"
            msg += f"\U0001f3e2 \u516c\u53f8\uff1a<b>{issuer_name} ({ticker})</b>\n"
            msg += f"\U0001f4b2 \u80a1\u50f9\uff1a<b>{price_str}</b>\n"
            msg += f"\U0001f4ca \u5347\u8dcc\u5e45\uff1a<b>{change_str}</b>\n"
            msg += f"\U0001f9e0 <b>AI \u5206\u6790\uff1a</b>\n{ai_analysis}\n"
            msg += f"\U0001f517 <a href='{link}'>\u67e5\u770b SEC \u539f\u6587</a>"

            send_telegram_message(msg)

            supabase_insert({
                "source": "form144",
                "ticker": ticker,
                "company_name": issuer_name,
                "action": "\u26a0\ufe0f Form 144 \u62cb\u552e\u9810\u8b66",
                "price": current_price,
                "change_pct": change_pct,
                "ai_summary": ai_analysis,
                "sec_link": link
            })

            found_count += 1
            time.sleep(2)

        if found_count >= 5:
            break

except Exception as e:
    print(f"Form 144 engine error: {e}")
