import asyncio
import logging

from aiogram import Bot, Dispatcher

from profitist.bot.middleware import AuthMiddleware, DbSessionMiddleware, SchedulerMiddleware
from profitist.bot.router import router
from profitist.config import settings
from profitist.scheduler.engine import scheduler
from profitist.scheduler.jobs import (
    proactive_daily_check,
    recover_pending_tasks,
    set_bot_instance,
    summarize_old_conversations,
)

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def _run() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    # Middleware (порядок важен: auth → db session → scheduler)
    router.message.middleware(AuthMiddleware())
    router.message.middleware(DbSessionMiddleware())
    router.message.middleware(SchedulerMiddleware(scheduler))
    dp.include_router(router)

    # Scheduler
    set_bot_instance(bot, settings.telegram_chat_id)
    await recover_pending_tasks(scheduler)
    scheduler.add_job(
        proactive_daily_check,
        "cron",
        hour=settings.proactive_check_hour,
        id="proactive_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        summarize_old_conversations,
        "interval",
        hours=settings.summarize_interval_hours,
        id="summarize_conversations",
        replace_existing=True,
    )
    scheduler.start()

    logger.info("Bot started. Scheduler running.")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
