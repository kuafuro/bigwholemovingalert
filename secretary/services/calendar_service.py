import base64
import json
import logging
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import config

logger = logging.getLogger(__name__)
HKT = timezone(timedelta(hours=8))
SCOPES = ['https://www.googleapis.com/auth/calendar']


def _load_credentials(token_b64: str = None):
    token_b64 = token_b64 or config.GOOGLE_TOKEN_B64
    if not token_b64:
        return None
    try:
        token_json = base64.b64decode(token_b64).decode()
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    except Exception as e:
        logger.error(f"Calendar credentials error: {e}")
        return None


class CalendarService:
    def __init__(self, token_b64: str = None):
        self._token_b64 = token_b64  # None = use default from config
        self._creds = None

    def _get_service(self):
        if not self._creds or not self._creds.valid:
            self._creds = _load_credentials(self._token_b64)
        if not self._creds:
            return None
        return build('calendar', 'v3', credentials=self._creds, cache_discovery=False)

    def get_events(self, date_str: str) -> str:
        service = self._get_service()
        if not service:
            return "⚠️ Google Calendar 未連接（GOOGLE_TOKEN_B64 未設定）"
        try:
            day = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=HKT)
            time_min = day.isoformat()
            time_max = (day + timedelta(days=1)).isoformat()
            result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = result.get('items', [])
            if not events:
                return f"📅 {date_str} 沒有行程"
            lines = [f"📅 {date_str} 行程："]
            for e in events:
                start = e['start'].get('dateTime', e['start'].get('date', ''))
                if 'T' in start:
                    t = datetime.fromisoformat(start).astimezone(HKT).strftime('%H:%M')
                else:
                    t = '全天'
                lines.append(f"  • {t} {e.get('summary', '（無標題）')} [ID:{e['id']}]")
            return "\n".join(lines)
        except Exception as e:
            return f"查詢失敗：{e}"

    def add_event(self, title: str, date: str, time: str, duration_minutes: int = 60,
                  description: str = "") -> str:
        service = self._get_service()
        if not service:
            return "⚠️ Google Calendar 未連接"
        try:
            start_dt = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M').replace(tzinfo=HKT)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            event = {
                'summary': title,
                'description': description,
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Hong_Kong'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Hong_Kong'},
            }
            created = service.events().insert(calendarId='primary', body=event).execute()
            return f"✅ 已新增：{title}（{date} {time}，{duration_minutes}分鐘）\nID: {created['id']}"
        except Exception as e:
            return f"新增失敗：{e}"

    def update_event(self, event_id: str, title: str = None, date: str = None,
                     time: str = None, duration_minutes: int = None,
                     description: str = None) -> str:
        service = self._get_service()
        if not service:
            return "⚠️ Google Calendar 未連接"
        try:
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            if title:
                event['summary'] = title
            if description is not None:
                event['description'] = description
            if date or time:
                # Rebuild start/end from existing or new values
                old_start = event['start'].get('dateTime', '')
                if old_start:
                    old_dt = datetime.fromisoformat(old_start).astimezone(HKT)
                    use_date = date or old_dt.strftime('%Y-%m-%d')
                    use_time = time or old_dt.strftime('%H:%M')
                    if duration_minutes is None:
                        old_end = event['end'].get('dateTime', '')
                        end_dt = datetime.fromisoformat(old_end).astimezone(HKT)
                        duration_minutes = int((end_dt - old_dt).total_seconds() // 60)
                    start_dt = datetime.strptime(f"{use_date} {use_time}", '%Y-%m-%d %H:%M').replace(tzinfo=HKT)
                    end_dt = start_dt + timedelta(minutes=duration_minutes)
                    event['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Hong_Kong'}
                    event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Hong_Kong'}
            elif duration_minutes is not None:
                old_start = event['start'].get('dateTime', '')
                start_dt = datetime.fromisoformat(old_start).astimezone(HKT)
                end_dt = start_dt + timedelta(minutes=duration_minutes)
                event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Hong_Kong'}
            updated = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            return f"✅ 已更新：{updated.get('summary')}（ID: {event_id}）"
        except Exception as e:
            return f"更新失敗：{e}"

    def delete_event(self, event_id: str) -> str:
        service = self._get_service()
        if not service:
            return "⚠️ Google Calendar 未連接"
        try:
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            return f"✅ 已刪除事件（ID: {event_id}）"
        except Exception as e:
            return f"刪除失敗：{e}"
