import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import os
import re

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE') 
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={'chat_id': CHAT_ID_WHALE, 'text': message, 'parse_mode': 'HTML'})

# 🌟 V25 新武裝：下載 SEC 官方「身分證(CIK) 轉 股票編號(Ticker)」字典庫
def get_sec_ticker_map():
    headers = {'User-Agent': 'WhaleRadar (your_email@example.com)'}
    try:
        resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
        data = resp.json()
        # 建立對應表，例如 {"1318605": "TSLA"}
        return {str(v['cik_str']): v['ticker'] for v in data.values()}
    except Exception as e:
        print(f"Ticker 字典庫下載失敗: {e}")
        return {}

# 系統啟動時立刻武裝字典庫
CIK_TICKER_MAP = get_sec_ticker_map()

headers = {'User-Agent': 'WhaleRadar (your_email@example.com)'}
url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&owner=only&count=40&output=atom'

now_utc = datetime.now(timezone.utc)
time_limit = now_utc - timedelta(minutes=5, seconds=30)

try:
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'xml')
    entries = soup.find_all('entry')

    found_count = 0

    for entry in entries:
        updated_tag = entry.find('updated')
        if not updated_tag:
            continue
            
        updated_str = updated_tag.text
        
        try:
            if datetime.fromisoformat(updated_str.replace('Z', '+00:00')).astimezone(timezone.utc) < time_limit: 
                break
        except Exception:
            continue
            
        link = entry.link['href']
        
        # 🎯 提取公司名稱 (從標題)
        title_text = entry.title.text if entry.title else ""
        title_match = re.search(r'-\s*(.+?)\s*\(', title_text)
        issuer_name = title_match.group(1).strip() if title_match else "未知公司"
        
        # 🎯 V25 終極神射手：從標題拔出 CIK，並用字典轉換為 Ticker！
        # 標題格式通常為："144 - TESLA, INC. (0001318605) (Subject)"
        ticker = "N/A"
        cik_match = re.search(r'\((\d+)\)\s*\(Subject\)', title_text)
        if cik_match:
            cik_str = str(int(cik_match.group(1))) # 轉整數以去除開頭的 0，再轉回字串
            ticker = CIK_TICKER_MAP.get(cik_str, "N/A")
            
        # 📊 呼叫 Finnhub 毫秒級 API 獲取報價
        price_str = "N/A"
        change_str = "N/A"
        
        if ticker != "N/A" and FINNHUB_API_KEY:
            try:
                finnhub_url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
                fh_resp = requests.get(finnhub_url)
                
                if fh_resp.status_code == 200:
                    data = fh_resp.json()
                    current_price = data.get('c', 0) 
                    change_pct = data.get('dp', 0)   
                    
                    if current_price and current_price > 0:
                        price_str = f"${current_price:.2f}"
                        sign = "+" if change_pct > 0 else ""
                        icon = "🟢" if change_pct > 0 else ("🔴" if change_pct < 0 else "⚪")
                        change_str = f"{icon} {sign}{change_pct:.2f}%"
            except Exception as e:
                print(f"Finnhub API 索取失敗: {e}")
        
        msg = f"🚨 <b>【Form 144 內部高管逃生預警】</b>\n"
        msg += f"🏢 公司：<b>{issuer_name} ({ticker})</b>\n"
        msg += f"💲 股價：<b>{price_str}</b>\n"
        msg += f"📊 升跌幅：<b>{change_str}</b>\n"
        msg += f"⚠️ <b>注意：有內部人士已提交拋售意向書！</b>\n"
        msg += f"🔗 <a href='{link}'>查看 SEC 原文</a>"
        
        send_telegram_message(msg)
        
        found_count += 1
        time.sleep(1.5)
            
    if found_count >= 4:
        break
        
except Exception as e:
    print(f"Form 144 執行失敗: {e}")
