# Планировщик

## Стек

**APScheduler 3.x** с `AsyncIOScheduler` — работает в том же event loop, что и бот.

Job persistence через SQLAlchemy jobstore (`data/jobs.db`) — задачи переживают перезапуск процесса.

## Типы задач

### 1. Явные задачи пользователя

Создаются агентом через инструменты `schedule_reminder` / `schedule_research`.

```
APScheduler fires → scheduler/jobs.py::execute_task(task_id)
  ├── "reminder"  → отправить текст напоминания через send_telegram_message
  └── "research"  → web_search → синтез через Claude (Sonnet) → send_telegram_message
→ обновить task.status = "done"
```

### 2. Ежедневная проактивная проверка

Cron-задание, запускается в `PROACTIVE_CHECK_HOUR` (UTC, default: 9:00).

```
proactive_daily_check()
  → загрузить user_facts
  → если фактов достаточно:
      → запрос к Claude (Sonnet):
        "Есть ли что-то ценное поделиться с пользователем сегодня?
         Если да — вызови web_search и send_telegram_message.
         Если нет — ничего не делай."
  → записать в proactive_log (защита от спама)
```

### 3. Фоновая суммаризация памяти

Cron-задание, запускается каждые `SUMMARIZE_INTERVAL_HOURS` (default: 6).

```
summarize_old_conversations()
  → взять необработанные conversations (processed_at IS NULL, старше 24ч)
  → если < SUMMARIZE_MIN_MESSAGES → выйти
  → Haiku: создать episode {summary, topics}
  → Haiku: извлечь новые user_facts
  → сохранить episode, upsert facts
  → проставить processed_at у обработанных строк
```

Использует Haiku — дешёвая пакетная обработка.

## Настройка (`scheduler/engine.py`)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url="sqlite:///data/jobs.db")},
    job_defaults={"coalesce": True, "max_instances": 1},
    timezone="UTC",
)
```

## Регистрация в `main.py`

```python
scheduler.start()
scheduler.add_job(proactive_daily_check, "cron", hour=settings.proactive_check_hour)
scheduler.add_job(summarize_old_conversations, "interval", hours=settings.summarize_interval_hours)
```

Одноразовые задачи (reminder, research) добавляются динамически из `tools.py` при вызове агентом.
