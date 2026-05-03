# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**profitist-2.0** — персональный ИИ-ассистент (проактивный Telegram-бот с долгосрочной памятью). Python 3.14+, managed with [uv](https://docs.astral.sh/uv/).

## Commands

```bash
uv sync                                # установить зависимости
uv run alembic upgrade head            # применить миграции
uv run alembic revision --autogenerate -m "desc"  # создать миграцию
uv run profitist                       # запустить бота
uv run pytest                          # тесты
uv run pytest tests/test_file.py::test_name  # один тест
```

## Architecture

Подробная документация в `docs/` — overview, memory, agent, database, scheduler, bot, setup.

Ключевые решения:
- **Роутинг моделей**: classify_intent (gpt-4o-mini) → выбор модели (gpt-4o-mini для memory/schedule, gpt-4o для chat/research)
- **Трёхуровневая память**: user_facts (всегда) + episodes (релевантные) + working memory (последние N реплик)
- **Фоновая суммаризация**: conversations → episodes + facts extraction (gpt-4o-mini, каждые 6ч)
- **Единственная точка доступа к БД**: `memory/store.py`
- **Авторизация**: только TELEGRAM_CHAT_ID

## Config

Все настройки через `.env` (см. `.env.example`). Обязательные: `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `TELEGRAM_CHAT_ID`, `DATABASE_URL`.

По умолчанию запросы идут через `API_BASE_URL=https://api.aitunnel.ru/v1/` (OpenAI-совместимый прокси). Чтобы использовать OpenAI напрямую — убери или замени эту переменную.
