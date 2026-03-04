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

from utils.supabase import supabase_insert, supabase_link_exists
from utils.finnhub import get_stock_quote
from utils.telegram import send_test_telegram, send_telegram_photo, send_whale_telegram

MIN_WHALE_AMOUNT = 500000
STRICT_WATCHLIST = True


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
        print(f"⚠️ S&P 500 list failed: {e}")
        return set()


def main():
    now_utc = datetime.now(timezone.utc)

    if now_utc.hour % 3 == 0 and now_utc.minute < 5:
        send_test_telegram(f"✅ V22 Whale Radar online! (UTC {now_utc.strftime('%H:%M')})")

    sp500_tickers = get_sp500_tickers()
    headers = {'User-Agent': 'WhaleRadarBot Admin@kuafuorhk.com'}
    url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=40&output=atom'
    time_limit = now_utc - timedelta(minutes=15)

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'xml')
    entries = soup.find_all('entry')
    print(f"📡 Found {len(entries)} Form 4 entries")
    found_count = 0

    for entry in entries:
        link = entry.link['href']
        updated_str = entry.updated.text

        try:
            if datetime.fromisoformat(updated_str.replace('Z', '+00:00')).astimezone(timezone.utc) < time_limit:
                break
        except Exception:
            continue

        if supabase_link_exists(link):
            continue

        txt_link = link.replace('-index.htm', '.txt')
        txt_response = requests.get(txt_link, headers=headers)

        if txt_response.status_code != 200:
            continue

        xml_soup = BeautifulSoup(txt_response.content, 'xml')
        try:
            issuer_name = xml_soup.find('issuerName').text if xml_soup.find('issuerName') else "Unknown"
            reporter_name = xml_soup.find('rptOwnerName').text if xml_soup.find('rptOwnerName') else "Unknown"
            ticker_tag = xml_soup.find('issuerTradingSymbol')
            ticker = ticker_tag.text.strip().upper() if ticker_tag else "N/A"

            if STRICT_WATCHLIST and sp500_tickers and (ticker not in sp500_tickers):
                continue

            transactions = xml_soup.find_all('nonDerivativeTransaction')
            if not transactions:
                continue

            price_str, change_str, current_price, change_pct = get_stock_quote(ticker)

            msg = f"🐋 <b>【頂級大鯨魚警報】</b>\n"
            msg += f"🏢 {issuer_name} (${ticker})\n"
            msg += f"👤 {reporter_name}\n"
            msg += f"💲 股價: <b>{price_str}</b>  {change_str}\n"
            is_whale = False
            target_price = 0
            action = ""
            shares = 0
            total_value = 0

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
                except Exception:
                    total_value = 0
                    post_shares = -1

                action = "🟢 買入" if tx_code == 'P' else "🔴 賣出"
                intent_label = ""
                if tx_code == 'P' and shares == post_shares and shares > 0:
                    intent_label = "\n🚀 【強烈看多：首次新建倉！】"
                elif tx_code == 'S' and post_shares == 0:
                    intent_label = "\n💀 【強烈看空：已清倉跳船！】"

                if total_value >= MIN_WHALE_AMOUNT:
                    is_whale = True
                    msg += f"👉 {action}: {shares:,.0f} 股\n💰 總額: ${total_value:,.0f} (@${price}){intent_label}\n"

            msg += f"🔗 <a href='{link}'>查看 SEC 來源</a>"

            if not is_whale:
                continue

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
                "extra_data": json.dumps({"tx_price": target_price})
            })
            if not inserted:
                print(f"    Skipped: already in DB or insert failed")
                continue

            filename = f"{ticker}_chart.png"
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=180)
                df = yf.download(ticker, start=start_date, end=end_date, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                if not df.empty:
                    mpf.plot(df, type='candle', style='charles',
                             title=f"{ticker} 6M K-Line (Whale: ${target_price})",
                             hlines=dict(hlines=[target_price], colors=['r'], linestyle='--'),
                             savefig=filename)
                    send_telegram_photo(msg, filename)
                else:
                    send_whale_telegram(msg)
            except Exception as e:
                print(f"Chart error: {e}")
                send_whale_telegram(msg)
            finally:
                if os.path.exists(filename):
                    os.remove(filename)

            found_count += 1
            time.sleep(1.5)

        except Exception as e:
            print(f"Parse error: {e}")

        if found_count >= 3:
            break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Form 4 engine error: {e}")
# ==================== END ====================
