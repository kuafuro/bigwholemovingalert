import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import os
import google.generativeai as genai

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("Gemini AI engine started")
else:
    print("Warning: GEMINI_API_KEY not set")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.get(url, params={'chat_id': CHAT_ID_WHALE, 'text': message, 'parse_mode': 'HTML'})
    if resp.status_code != 200:
        print(f"Telegram send failed: {resp.status_code}")

headers = {'User-Agent': 'WhaleRadarBot Admin@kuafuorhk.com'}
url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=only&count=40&output=atom'

now_utc = datetime.now(timezone.utc)
time_limit = now_utc - timedelta(minutes=15)

try:
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'xml')
    entries = soup.find_all('entry')
    print(f"Found {len(entries)} 8-K entries")
    found_count = 0

    for entry in entries:
        updated_str = entry.updated.text
        try:
            if datetime.fromisoformat(updated_str.replace('Z', '+00:00')).astimezone(timezone.utc) < time_limit:
                break
        except Exception:
            continue

        link = entry.link['href']
        company_name = entry.title.text.split(' - ')[0].strip() if entry.title else "Unknown"

        if not model:
            print("Gemini not initialized, skipping")
            break

        txt_link = link.replace('-index.htm', '.txt')
        txt_response = requests.get(txt_link, headers=headers)

        if txt_response.status_code == 200:
            content = txt_response.text[:15000]
            prompt = (
                "This is a partial US SEC 8-K filing. Act as a professional Wall Street analyst. "
                "Summarize the key points in Traditional Chinese in 3-5 sentences. "
                "Judge if this filing is bullish, bearish, or neutral for the stock price. "
                "Use emoji: rocket=bullish, chart_down=bearish, neutral=neutral.\n\n"
                f"Filing content:\n{content}"
            )

            try:
                ai_response = model.generate_content(prompt)
                summary = ai_response.text.strip()

                msg = (
                    "\U0001f916 <b>\u3010AI 8-K \u8ca1\u5831\u79d2\u8b80\u6a5f\u3011</b>\n"
                    f"\U0001f3e2 \u516c\u53f8: <b>{company_name}</b>\n"
                    f"\U0001f4dd <b>AI \u7e3d\u7d50:</b>\n{summary}\n\n"
                    f"\U0001f517 <a href='{link}'>\u67e5\u770b 8-K \u539f\u6587</a>"
                )

                send_telegram_message(msg)
                print(f"  Sent: {company_name}")
                found_count += 1
                time.sleep(2)
            except Exception as e:
                print(f"AI parse failed: {e}")

        if found_count >= 3:
            break

except Exception as e:
    print(f"AI analyst error: {e}")
