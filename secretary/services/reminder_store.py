import logging
import uuid
from datetime import datetime

from apscheduler.jobstores.base import JobLookupError

from services.scheduler import get_scheduler

logger = logging.getLogger(__name__)

_app = None
_reminders: dict[str, dict] = {}


def set_app(app) -> None:
    global _app
    _app = app


def add_reminder(chat_id: int, message: str, remind_at: datetime) -> str:
    reminder_id = str(uuid.uuid4())[:8]

    async def _send():
        if _app:
            await _app.bot.send_message(chat_id=chat_id, text=f"⏰ 提醒：{message}")
        _reminders.pop(reminder_id, None)

    get_scheduler().add_job(_send, "date", run_date=remind_at, id=reminder_id)
    _reminders[reminder_id] = {
        "id": reminder_id,
        "message": message,
        "remind_at": remind_at,
        "chat_id": chat_id,
    }
    logger.info(f"Reminder {reminder_id} set for {remind_at} (chat {chat_id})")
    return reminder_id


def list_reminders(chat_id: int) -> list[dict]:
    return [r for r in _reminders.values() if r["chat_id"] == chat_id]


def cancel_reminder(reminder_id: str) -> bool:
    if reminder_id not in _reminders:
        return False
    try:
        get_scheduler().remove_job(reminder_id)
    except JobLookupError:
        pass
    del _reminders[reminder_id]
    return True
