# ==================== whale.py V22 全面升級版 ====================
# 引擎一：Form 4 大鯨魚警報
# 升級：Supabase + Finnhub + 新版 Gemini SDK + 防重複
# ================================================================
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import os
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import json

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_TEST = os.environ.get('TELEGRAM_CHAT_ID_TEST')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE')
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

MIN_WHALE_AMOUNT = 500000
STRICT_WATCHLIST = True

now_utc = datetime.now(timezone.utc)

# ===== Supabase 工具函數 =====
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
        if resp.status_code == 201:
            return True
        elif resp.status_code == 409:
            print(f"  ⏭️ 重複記錄，已跳過")
            return False
        else:
            print(f"  ⚠️ Supabase 寫入失敗: {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ⚠️ Supabase 錯誤: {e}")
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

# ===== Finnhub 股價查詢 =====
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
    except Exception as e:
        print(f"  \u26a0\ufe0f Finnhub error: {e}")
    return "N/A", "N/A", 0, 0

# ===== S&P 500 清單 =====
def get_sp500_tickers():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, 'html.parser')
        tickers = set()
        for row in soup.find('table', {'id': 'constituents'}).find_all('tr')[1:]:
            t = row.find_all('td')[0].text.strip()
            tickers.add(t)
            tickers.add(t.replace('.', '-'))
        return tickers
    except Exception as e:
        print(f"\u26a0\ufe0f S&P 500 list failed: {e}")
        return set()

SP500_TICKERS = get_sp500_tickers()

# ===== Telegram =====
def send_test_telegram(message):
    if not CHAT_ID_TEST:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.get(url, params={'chat_id': CHAT_ID_TEST, 'text': message})
    if resp.status_code == 200:
        print(f"\U0001f4e1 Heartbeat sent")
    else:
        print(f"\u274c Heartbeat failed: {resp.status_code}")

def send_telegram_photo(caption, photo_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={'chat_id': CHAT_ID_WHALE, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': photo})

def send_whale_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={'chat_id': CHAT_ID_WHALE, 'text': message, 'parse_mode': 'HTML'})

# ===== Heartbeat =====
if now_utc.hour % 3 == 0 and now_utc.minute <= 25:
    send_test_telegram(f"\u2705 V22 Whale Radar online! (UTC {now_utc.strftime('%H:%M')})")

# ===== Main =====
headers = {'User-Agent': 'WhaleRadarBot Admin@kuafuorhk.com'}
url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=40&output=atom'
time_limit = now_utc - timedelta(minutes=15)

try:
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'xml')
    entries = soup.find_all('entry')
    print(f"\U0001f4e1 Found {len(entries)} Form 4 entries")
    found_count = 0

    for entry in entries:
        link = entry.link['href']
        updated_str = entry.updated.text

        try:
            if datetime.fromisoformat(updated_str.replace('Z', '+00:00')).astimezone(timezone.utc) < time_limit:
                break
        except:
            continue

        if supabase_link_exists(link):
            continue

        txt_link = link.replace('-index.htm', '.txt')
        txt_response = requests.get(txt_link, headers=headers)

        if txt_response.status_code == 200:
            xml_soup = BeautifulSoup(txt_response.content, 'xml')
            try:
                issuer_name = xml_soup.find('issuerName').text if xml_soup.find('issuerName') else "Unknown"
                reporter_name = xml_soup.find('rptOwnerName').text if xml_soup.find('rptOwnerName') else "Unknown"
                ticker_tag = xml_soup.find('issuerTradingSymbol')
                ticker = ticker_tag.text.strip().upper() if ticker_tag else "N/A"

                if STRICT_WATCHLIST and SP500_TICKERS and (ticker not in SP500_TICKERS):
                    continue

                transactions = xml_soup.find_all('nonDerivativeTransaction')
                if transactions:
                    price_str, change_str, current_price, change_pct = get_stock_quote(ticker)

                    msg = f"\U0001f40b <b>\u3010\u9802\u7d1a\u5927\u9be8\u9b5a\u8b66\u5831\u3011</b>\n"
                    msg += f"\U0001f3e2 {issuer_name} (${ticker})\n"
                    msg += f"\U0001f464 {reporter_name}\n"
                    msg += f"\U0001f4b2 \u80a1\u50f9: <b>{price_str}</b>  {change_str}\n"
                    is_whale = False
                    target_price = 0

                    for txn in transactions:
                        coding_tag = txn.find('transactionCoding')
                        tx_code = coding_tag.find('transactionCode').text if coding_tag and coding_tag.find('transactionCode') else ""
                        if tx_code not in ['P', 'S']:
                            continue

                        shares_tag = txn.find('transactionShares')
                        shares_str = shares_tag.find('value').text if shares_tag and shares_tag.find('value') else "0"
                        price_tag = txn.find('transactionPricePerShare')
                        price_val_str = price_tag.find('value').text if price_tag and price_tag.find('value') else "0"
                        post_tag = txn.find('sharesOwnedFollowingTransaction')
                        post_str = post_tag.find('value').text if post_tag and post_tag.find('value') else "-1"

                        try:
                            shares = float(shares_str)
                            price = float(price_val_str)
                            post_shares = float(post_str)
                            total_value = shares * price
                            target_price = price
                        except:
                            total_value = 0
                            post_shares = -1

                        action = "\U0001f7e2 \u8cb7\u5165" if tx_code == 'P' else "\U0001f534 \u8ce3\u51fa"
                        intent_label = ""
                        if tx_code == 'P' and shares == post_shares and shares > 0:
                            intent_label = "\n\U0001f680 \u3010\u5f37\u70c8\u770b\u591a\uff1a\u9996\u6b21\u65b0\u5efa\u5009\uff01\u3011"
                        elif tx_code == 'S' and post_shares == 0:
                            intent_label = "\n\U0001f480 \u3010\u5f37\u70c8\u770b\u7a7a\uff1a\u5df2\u6e05\u5009\u8df3\u8239\uff01\u3011"

                        if total_value >= MIN_WHALE_AMOUNT:
                            is_whale = True
                            msg += f"\U0001f449 {action}: {shares:,.0f} \u80a1\n\U0001f4b0 \u7e3d\u984d: ${total_value:,.0f} (@${price}){intent_label}\n"

                    msg += f"\U0001f517 <a href='{link}'>\u67e5\u770b SEC \u4f86\u6e90</a>"

                    if is_whale:
                        # Write to DB FIRST to prevent duplicates
                        inserted = supabase_insert({
                            "source": "form4",
                            "ticker": ticker,
                            "company_name": issuer_name,
                            "action": action,
                            "reporter_name": reporter_name,
                            "shares": shares,
                            "total_value": total_value,
                            "price": current_price,
                            "change_pct": change_pct,
                            "sec_link": link,
                            "extra_data": json.dumps({"intent": intent_label.strip(), "tx_price": price})
                        })
                        if not inserted:
                            print(f"    Skipped: already in DB or insert failed")
                            continue

                        try:
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=180)
                            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
                            if isinstance(df.columns, pd.MultiIndex):
                                df.columns = df.columns.droplevel(1)
                            if not df.empty:
                                filename = f"{ticker}_chart.png"
                                mpf.plot(df, type='candle', style='charles',
                                         title=f"{ticker} 6M K-Line (Whale: ${target_price})",
                                         hlines=dict(hlines=[target_price], colors=['r'], linestyle='--'),
                                         savefig=filename)
                                send_telegram_photo(msg, filename)
                                os.remove(filename)
                            else:
                                send_whale_telegram(msg)
                        except Exception as e:
                            print(f"Chart error: {e}")
                            send_whale_telegram(msg)

                        found_count += 1
                        time.sleep(1.5)
            except Exception as e:
                print(f"Parse error: {e}")

        if found_count >= 3:
            break

except Exception as e:
    print(f"Form 4 engine error: {e}")
# ==================== END ====================