from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(
    job_defaults={"coalesce": True, "max_instances": 1},
    timezone="UTC",
)
