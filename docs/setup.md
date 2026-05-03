# Настройка и запуск

## Требования

- Python 3.14+
- PostgreSQL (локально или облако)
- uv

## Переменные окружения

Скопируй `.env.example` в `.env` и заполни:

| Переменная | Обязательная | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | да | токен от @BotFather |
| `ANTHROPIC_API_KEY` | да | ключ Anthropic API |
| `TELEGRAM_CHAT_ID` | да | твой chat_id (узнать через @userinfobot) |
| `DATABASE_URL` | да | `postgresql+asyncpg://user:pass@host:5432/db` |
| `TAVILY_API_KEY` | нет | если пусто — web_search недоступен |
| `CLAUDE_SONNET_MODEL` | нет | default: `claude-sonnet-4-6` |
| `CLAUDE_HAIKU_MODEL` | нет | default: `claude-haiku-4-5-20251001` |
| `PROACTIVE_CHECK_HOUR` | нет | час UTC для проактивной проверки (default: 9) |
| `SUMMARIZE_INTERVAL_HOURS` | нет | интервал суммаризации в часах (default: 6) |

## Запуск

```bash
# 1. Установить зависимости
uv sync

# 2. Применить миграции БД
uv run alembic upgrade head

# 3. Запустить бота
uv run profitist
```

## Миграции

```bash
# Создать миграцию после изменения моделей
uv run alembic revision --autogenerate -m "add episodes table"

# Применить
uv run alembic upgrade head

# Откатить
uv run alembic downgrade -1
```

## Тесты

```bash
uv run pytest                          # все тесты
uv run pytest tests/test_memory_store.py  # один файл
uv run pytest -k "test_upsert_fact"   # один тест
```
