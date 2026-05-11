import json
import logging
from datetime import datetime, timezone

import openai

from profitist.config import settings
from profitist.db.base import AsyncSessionLocal
from profitist.memory import store
from profitist.search.tavily import search as tavily_search
from profitist.memory.store import get_pending_tasks, update_task_status

logger = logging.getLogger(__name__)

_client = openai.AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.api_base_url,
)

# These are set in main.py at startup
_bot = None
_chat_id: int | None = None


def set_bot_instance(bot, chat_id: int) -> None:
    global _bot, _chat_id
    _bot = bot
    _chat_id = chat_id


async def _send_message(text: str) -> None:
    if _bot is None or _chat_id is None:
        logger.error("Bot instance not set. Call set_bot_instance() first.")
        return
    await _bot.send_message(_chat_id, text)


# --- Recovery at startup ---


async def recover_pending_tasks(scheduler) -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        tasks = await get_pending_tasks(session)
        recovered = 0
        missed = 0
        for task in tasks:
            if task.scheduled_at is None:
                continue
            scheduled_utc = task.scheduled_at.replace(tzinfo=timezone.utc)
            if scheduled_utc <= now:
                await update_task_status(session, task.id, "failed", result="missed (bot was down)")
                missed += 1
            else:
                scheduler.add_job(
                    execute_task,
                    "date",
                    run_date=scheduled_utc,
                    args=[task.id],
                    id=task.apscheduler_job_id,
                    replace_existing=True,
                )
                recovered += 1
    if recovered or missed:
        logger.info("Recovery: %d tasks re-scheduled, %d marked missed", recovered, missed)


# --- Task execution ---


async def execute_task(task_id: int) -> None:
    async with AsyncSessionLocal() as session:
        task = await store.get_task(session, task_id)
        if task is None:
            logger.error("Task %d not found", task_id)
            return

        if task.status != "pending":
            logger.info("Task %d already %s, skipping", task_id, task.status)
            return

        await store.update_task_status(session, task_id, "in_progress")

        try:
            if task.task_type == "reminder":
                text = await _generate_reminder_text(task.description)
                await _send_message(text)
                await store.update_task_status(session, task_id, "done")

            elif task.task_type == "research":
                result = await _do_research(task.description)
                await _send_message(result)
                await store.update_task_status(session, task_id, "done", result=result)

            else:
                logger.warning("Unknown task type: %s", task.task_type)
                await store.update_task_status(session, task_id, "failed", result="Unknown task type")

        except Exception:
            logger.exception("Failed to execute task %d", task_id)
            await store.update_task_status(session, task_id, "failed")


async def _generate_reminder_text(description: str) -> str:
    try:
        response = await _client.chat.completions.create(
            model=settings.main_model,
            max_tokens=300,
            temperature=0.9,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты дружелюбный ассистент. Тебе дали тему напоминания. "
                        "Сформулируй её живо и кратко (1–2 предложения), без шаблонных фраз вроде «Напоминание:». "
                        "Можешь добавить уместное эмодзи. Не выдумывай детали — только перефразируй."
                    ),
                },
                {"role": "user", "content": f"Тема напоминания: {description}"},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception("Failed to generate reminder text, using fallback")
        return f"🔔 {description}"


async def _do_research(description: str) -> str:
    search_results = await tavily_search(description)

    response = await _client.chat.completions.create(
        model=settings.main_model,
        max_tokens=2048,
        messages=[
            {
                "role": "system",
                "content": "Ты — исследовательский ассистент. Синтезируй результаты поиска в краткий, полезный обзор на русском языке.",
            },
            {
                "role": "user",
                "content": f"Задача: {description}\n\nРезультаты поиска:\n{search_results}\n\nСоздай структурированный обзор.",
            },
        ],
    )
    return response.choices[0].message.content


# --- Proactive daily check ---


async def proactive_daily_check() -> None:
    async with AsyncSessionLocal() as session:
        facts = await store.get_all_user_facts(session)
        if len(facts) < 3:
            logger.info("Not enough user facts for proactive check (%d), skipping", len(facts))
            return

        facts_text = "\n".join(f"- {f.key}: {f.value}" for f in facts)

        response = await _client.chat.completions.create(
            model=settings.main_model,
            max_tokens=1024,
            temperature=0.9,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — проактивный персональный ассистент. Тебе известны факты о пользователе. "
                        "Определи, есть ли что-то ценное, чем стоит поделиться сегодня — полезный инсайт, "
                        "напоминание о цели, актуальная мысль. Если нет — ответь пустой строкой. "
                        "Если да — напиши короткое дружелюбное сообщение. Варьируй стиль и формулировки."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Факты о пользователе:\n{facts_text}\n\nСегодня: {datetime.now(timezone.utc):%Y-%m-%d}",
                },
            ],
        )

        message = response.choices[0].message.content.strip()
        if not message:
            logger.info("Proactive check: nothing to share today")
            return

        await _send_message(message)
        await store.log_proactive_message(session, trigger="daily_check", message_sent=message)
        logger.info("Proactive message sent")


# --- Background summarization ---


async def summarize_old_conversations() -> None:
    async with AsyncSessionLocal() as session:
        conversations = await store.get_unprocessed_conversations(
            session,
            older_than_hours=settings.summarize_older_than_hours,
            min_count=settings.summarize_min_messages,
        )
        if not conversations:
            logger.info("No conversations to summarize")
            return

        conv_text = "\n".join(
            f"[{c.role}] {c.content}" for c in conversations
        )

        response = await _client.chat.completions.create(
            model=settings.fast_model,
            max_tokens=512,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты суммаризатор диалогов. Получив диалог, создай:\n"
                        '1. Краткое резюме (2-3 предложения)\n'
                        '2. Список тем (3-5 ключевых слов)\n'
                        'Ответь строго в JSON: {"summary": "...", "topics": ["...", "..."]}'
                    ),
                },
                {"role": "user", "content": conv_text},
            ],
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)

        period_start = conversations[0].created_at
        period_end = conversations[-1].created_at

        await store.save_episode(
            session,
            summary=parsed["summary"],
            period_start=period_start,
            period_end=period_end,
            topics=parsed["topics"],
        )

        facts_response = await _client.chat.completions.create(
            model=settings.fast_model,
            max_tokens=512,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты извлекаешь факты о пользователе из диалога. "
                        "Верни JSON-массив объектов: "
                        '[{"key": "...", "value": "..."}]. '
                        "Если новых фактов нет — верни пустой массив []."
                    ),
                },
                {"role": "user", "content": conv_text},
            ],
        )

        facts_raw = facts_response.choices[0].message.content.strip()
        new_facts = json.loads(facts_raw)

        for fact in new_facts:
            await store.upsert_user_fact(session, key=fact["key"], value=fact["value"])

        ids = [c.id for c in conversations]
        await store.mark_conversations_processed(session, ids)

        logger.info(
            "Summarized %d conversations into episode, extracted %d facts",
            len(conversations),
            len(new_facts),
        )
