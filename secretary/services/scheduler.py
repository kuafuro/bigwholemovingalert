from apscheduler.schedulers.asyncio import AsyncIOScheduler

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Hong_Kong")
    return _scheduler
