import os
import requests

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')


def supabase_insert(data):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/whale_alerts", headers=headers, json=data)
        if resp.status_code == 201:
            return True
        elif resp.status_code == 409:
            print("  ⏭️ 重複記錄，已跳過")
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
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/whale_alerts",
            headers=headers,
            params={"sec_link": f"eq.{link}", "select": "id", "limit": 1}
        )
        return resp.status_code == 200 and len(resp.json()) > 0
    except Exception as e:
        print(f"  ⚠️ Supabase 查詢錯誤: {e}")
        return False


def supabase_patch(link, data):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/whale_alerts",
            headers=headers,
            params={"sec_link": f"eq.{link}"},
            json=data
        )
    except Exception as e:
        print(f"  ⚠️ Supabase patch 錯誤: {e}")
