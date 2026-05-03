from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from profitist.memory import store
from profitist.search.tavily import search as tavily_search

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "save_user_fact",
            "description": "Сохранить факт о пользователе в долгосрочную память. Используй когда пользователь сообщает что-то о себе.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Уникальный ключ факта, e.g. 'occupation', 'goal', 'preference:tone'",
                    },
                    "value": {
                        "type": "string",
                        "description": "Значение факта",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_context",
            "description": "Получить все известные факты о пользователе из долгосрочной памяти.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_reminder",
            "description": "Запланировать напоминание. Пользователь получит сообщение в указанное время.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Текст напоминания",
                    },
                    "scheduled_at": {
                        "type": "string",
                        "description": "Дата и время в формате ISO 8601, e.g. '2026-05-02T09:00:00Z'",
                    },
                },
                "required": ["description", "scheduled_at"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_research",
            "description": "Поставить задачу на исследование темы. Бот выполнит ресёрч и отправит результат.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Что нужно исследовать",
                    },
                    "scheduled_at": {
                        "type": "string",
                        "description": "Когда отправить результат (ISO 8601). Если пусто — выполнить как можно скорее.",
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Найти актуальную информацию в интернете. Используй для текущих событий, цен, новостей.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


async def execute_tool(
    name: str,
    input_data: dict,
    session: AsyncSession,
    scheduler=None,
    user_message: str | None = None,
) -> str:
    match name:
        case "save_user_fact":
            fact = await store.upsert_user_fact(
                session,
                key=input_data["key"],
                value=input_data["value"],
                source_message=user_message,
            )
            return f"Факт сохранён: {fact.key} = {fact.value}"

        case "get_user_context":
            facts = await store.get_all_user_facts(session)
            if not facts:
                return "Пока нет сохранённых фактов о пользователе."
            lines = [f"- {f.key}: {f.value}" for f in facts]
            return "\n".join(lines)

        case "schedule_reminder":
            scheduled_at = datetime.fromisoformat(input_data["scheduled_at"])
            if scheduled_at.tzinfo is not None:
                scheduled_at = scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)
            job_id = f"reminder_{uuid4().hex[:8]}"
            task = await store.create_task(
                session,
                task_type="reminder",
                description=input_data["description"],
                scheduled_at=scheduled_at,
                apscheduler_job_id=job_id,
            )
            if scheduler:
                from profitist.scheduler.jobs import execute_task

                scheduler.add_job(
                    execute_task,
                    "date",
                    run_date=scheduled_at,
                    args=[task.id],
                    id=job_id,
                )
            return f"Напоминание запланировано на {scheduled_at.isoformat()}"

        case "schedule_research":
            scheduled_at_str = input_data.get("scheduled_at")
            if scheduled_at_str:
                scheduled_at = datetime.fromisoformat(scheduled_at_str)
                if scheduled_at.tzinfo is not None:
                    scheduled_at = scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                scheduled_at = None
            job_id = f"research_{uuid4().hex[:8]}"
            task = await store.create_task(
                session,
                task_type="research",
                description=input_data["description"],
                scheduled_at=scheduled_at,
                apscheduler_job_id=job_id,
            )
            if scheduler:
                from profitist.scheduler.jobs import execute_task

                run_date = scheduled_at or datetime.now(timezone.utc)
                scheduler.add_job(
                    execute_task,
                    "date",
                    run_date=run_date,
                    args=[task.id],
                    id=job_id,
                )
            return f"Задача на исследование создана (id={task.id})"

        case "web_search":
            results = await tavily_search(input_data["query"])
            return results

        case _:
            raise ValueError(f"Unknown tool: {name}")
