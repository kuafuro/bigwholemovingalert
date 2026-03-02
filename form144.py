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

headers = {'User-Agent': 'MyFirstApp (your_email@example.com)'}
url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=144&owner=only&count=40&output=atom'

now_utc = datetime.now(timezone.utc)
# 🌟 戰術修正：將雷達波段縮小至 6 分鐘！完美覆蓋每 5 分鐘的巡邏，徹底消滅重複洗版！
time_limit = now_utc - timedelta(minutes=6)

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
        txt_link = link.replace('-index.htm', '.txt')
        
        txt_response = requests.get(txt_link, headers=headers)
        if txt_response.status_code == 200:
            txt_content = txt_response.text
            
            # 🎯 換上 Form 144 專用雙重狙擊鏡 (同時掃描 ISSUER 與 SUBJECT-COMPANY)
            issuer_match = re.search(r'<(?:ISSUER|SUBJECT-COMPANY)>.*?<CONFORMED-NAME>([^\n]+)', txt_content, re.DOTALL)
            issuer_name = issuer_match.group(1).strip() if issuer_match else "未知公司"
            
            msg = f"🚨 <b>【Form 144 內部高管逃生預警】</b>\n"
            msg += f"🏢 公司: <b>{issuer_name}</b>\n"
            msg += f"⚠️ <b>注意：有內部人士已提交拋售意向書！</b>\n"
            msg += f"🔗 <a href='{link}'>查看 SEC 原文</a>"
            
            send_telegram_message(msg)
            
            found_count += 1
            time.sleep(1.5)
                
        if found_count >= 3:
            break
            
except Exception as e:
    print(f"Form 144 執行失敗: {e}")