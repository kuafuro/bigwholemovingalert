import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import os
import re

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE') 
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY') # 🌟 接收總部配發的金鑰

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={'chat_id': CHAT_ID_WHALE, 'text': message, 'parse_mode': 'HTML'})

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
        
        # 🎯 提取公司名稱
        title_text = entry.title.text if entry.title else ""
        title_match = re.search(r'-\s*(.+?)\s*\(', title_text)
        issuer_name = title_match.group(1).strip() if title_match else "未知公司"
        
        txt_link = link.replace('-index.htm', '.txt')
        txt_response = requests.get(txt_link, headers=headers)
        
        if txt_response.status_code == 200:
            txt_content = txt_response.text
            
            # 🎯 狙擊股票編號 (Ticker)
            ticker_match = re.search(r'<issuerTradingSymbol>([^<]+)</issuerTradingSymbol>', txt_content, re.IGNORECASE)
            ticker = ticker_match.group(1).strip().upper() if ticker_match else "N/A"
            
            # 📊 V24 戰術核心：呼叫 Finnhub 毫秒級 API 獲取報價
            price_str = "N/A"
            change_str = "N/A"
            
            if ticker != "N/A" and FINNHUB_API_KEY:
                try:
                    # 直接索取 Quote 盤口快照
                    finnhub_url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
                    fh_resp = requests.get(finnhub_url)
                    
                    if fh_resp.status_code == 200:
                        data = fh_resp.json()
                        current_price = data.get('c', 0) # 現價
                        change_pct = data.get('dp', 0)   # 升跌幅(%)
                        
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
