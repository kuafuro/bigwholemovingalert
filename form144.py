import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import os
import re

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE') 

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={'chat_id': CHAT_ID_WHALE, 'text': message, 'parse_mode': 'HTML'})

headers = {'User-Agent': 'WhaleRadar (your_email@example.com)'}
url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&owner=only&count=40&output=atom'

now_utc = datetime.now(timezone.utc)
# 🌟 戰術修正：精準設定為 5.5 分鐘！完美銜接 GitHub 每 5 分鐘的排程，絕不重疊！
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
            # 強轉時區並驗證是否過期
            if datetime.fromisoformat(updated_str.replace('Z', '+00:00')).astimezone(timezone.utc) < time_limit: 
                break
        except Exception:
            continue
            
        link = entry.link['href']
        
        # 🎯 V22 終極神射手：直接從 SEC 標題中拔出公司名稱！
        # 標題格式通常為："144 - TESLA, INC. (0001318605) (Subject)"
        title_text = entry.title.text if entry.title else ""
        title_match = re.search(r'-\s*(.+?)\s*\(', title_text)
        issuer_name = title_match.group(1).strip() if title_match else "未知公司"
        
        msg = f"🚨 <b>【Form 144 內部高管逃生預警】</b>\n"
        msg += f"🏢 公司: <b>{issuer_name}</b>\n"
        msg += f"⚠️ <b>注意：有內部人士已提交拋售意向書！</b>\n"
        msg += f"🔗 <a href='{link}'>查看 SEC 原文</a>"
        
        send_telegram_message(msg)
        
        found_count += 1
        time.sleep(1.5)
                
        # 🛡️ 限制每次巡邏最多發送 4 筆，防止開盤潮過度洗版
        if found_count >= 4:
            break
            
except Exception as e:
    print(f"Form 144 執行失敗: {e}")
