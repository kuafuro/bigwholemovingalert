import os
import requests

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID_WHALE = os.environ.get('TELEGRAM_CHAT_ID_WHALE')
CHAT_ID_TEST = os.environ.get('TELEGRAM_CHAT_ID_TEST')


def send_whale_telegram(message):
    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={'chat_id': CHAT_ID_WHALE, 'text': message, 'parse_mode': 'HTML'}
    )


def send_telegram_photo(caption, photo_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(
            url,
            data={'chat_id': CHAT_ID_WHALE, 'caption': caption, 'parse_mode': 'HTML'},
            files={'photo': photo}
        )


def send_test_telegram(message):
    if not CHAT_ID_TEST:
        return
    resp = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={'chat_id': CHAT_ID_TEST, 'text': message}
    )
    if resp.status_code == 200:
        print("📡 Heartbeat sent")
    else:
        print(f"❌ Heartbeat failed: {resp.status_code}")
