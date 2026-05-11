from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from profitist.config import settings

scheduler = AsyncIOScheduler(
    job_defaults={"coalesce": True, "max_instances": 1},
    timezone=ZoneInfo(settings.user_timezone),
)
