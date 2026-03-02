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

# 🌟 V27 戰略偽裝：使用您的專屬企業網域，突破 SEC 防火牆封鎖！
SEC_HEADERS = {'User-Agent': 'WhaleRadarBot Admin@kuafuorhk.com'}

def get_sec_ticker_map():
    try:
        resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS)
        data = resp.json()
        return {str(v['cik_str']): v['ticker'] for v in data.values()}
    except Exception as e:
        print(f"Ticker 字典庫下載失敗: {e}")
        return {}

CIK_TICKER_MAP = get_sec_ticker_map()

url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&owner=only&count=40&output=atom'

now_utc = datetime.now(timezone.utc)
time_limit = now_utc - timedelta(minutes=5, seconds=30)

try:
    response = requests.get(url, headers=SEC_HEADERS)
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
        txt_link = link.replace('-index.htm', '.txt')
        txt_response = requests.get(txt_link, headers=SEC_HEADERS)
        
        if txt_response.status_code == 200:
            txt_content = txt_response.text
            
            ticker = "N/A"
            issuer_name = "未知公司"
            
            # 🎯 V27 第一重防線 (X光直擊)：直接掃描深層 XML 官方標籤，精準度 100%
            sym_match = re.search(r'<(?:issuerSymbol|issuerTradingSymbol)>([^<]+)</(?:issuerSymbol|issuerTradingSymbol)>', txt_content, re.IGNORECASE)
            if sym_match: ticker = sym_match.group(1).strip().upper()
            
            name_match = re.search(r'<(?:nameOfIssuer|issuerName)>([^<]+)</(?:nameOfIssuer|issuerName)>', txt_content, re.IGNORECASE)
            if name_match: issuer_name = name_match.group(1).strip()
            
            # 🎯 V27 第二重防線 (隔離防護)：嚴格限制 SGML 掃描區塊，防堵人名偽裝
            if ticker == "N/A" or issuer_name == "未知公司":
                sgml_block = re.search(r'(?:SUBJECT COMPANY|ISSUER):(.*?)(?:FILED BY:|REPORTING-OWNER:|<SEC-DOCUMENT>|</SEC-HEADER>)', txt_content, re.DOTALL | re.IGNORECASE)
                if sgml_block:
                    block = sgml_block.group(1)
                    if issuer_name == "未知公司":
                        c_name = re.search(r'COMPANY CONFORMED NAME:\s*([^\n\r]+)', block)
                        if c_name: issuer_name = c_name.group(1).strip()
                    if ticker == "N/A":
                        cik_m = re.search(r'CENTRAL INDEX KEY:\s*(\d+)', block)
                        if cik_m:
                            cik_str = str(int(cik_m.group(1).strip()))
                            ticker = CIK_TICKER_MAP.get(cik_str, "N/A")
            
            # 🎯 V27 第三重防線 (標題備用救援)：從最外層拔出身份證轉換
            if ticker == "N/A":
                title_text = entry.title.text if entry.title else ""
                cik_match_title = re.search(r'\((\d+)\)\s*\(Subject\)', title_text)
                if cik_match_title:
                     cik_str = str(int(cik_match_title.group(1)))
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
