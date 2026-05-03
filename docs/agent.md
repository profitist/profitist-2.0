# Агент

## Роутинг моделей (`agent/router.py`)

Перед каждым запросом — быстрый вызов Haiku (~50 токенов) для классификации намерения.

```python
INTENT_MODEL_MAP = {
    "memory":   "claude-haiku-4-5-20251001",  # запомни, сохрани, не забудь
    "schedule": "claude-haiku-4-5-20251001",  # напомни, поставь задачу
    "chat":     "claude-sonnet-4-6",          # обычный разговор
    "research": "claude-sonnet-4-6",          # поиск, исследование, ресёрч
}
```

`classify_intent(message) → str` — один вызов Haiku с `max_tokens=10`, строгий ответ одним словом.
Стоимость ~$0.00001. Позволяет использовать Haiku для всех простых операций.

Фоновая суммаризация — всегда Haiku.

## Agentic Loop (`agent/loop.py`)

Ручной цикл поверх Anthropic SDK (не Agent SDK — приложение само управляет памятью и доставкой).

```
run_agent_loop(user_message, context, model) → str

1. build_context(user_message) → facts + episodes + recent turns
2. build_system_prompt(context)
3. streaming call → anthropic.messages.stream()
4. stop_reason == "tool_use":
     execute each tool → append tool_results → continue loop
5. stop_reason == "end_turn":
     save to conversations → return text
```

- `thinking={"type": "adaptive"}` — включается для сложных задач (синтез ресёрча)
- Streaming через `.stream()` + `.get_final_message()` — избегает HTTP timeout при длинных цепочках инструментов
- Prompt caching: breakpoint после стабильного префикса системного промпта; динамический блок с фактами не кешируется

## System Prompt (`agent/prompts.py`)

Разбит на два блока:

```
[STABLE — кешируется]
Ты персональный ИИ-ассистент...
Правила использования инструментов...
<cache_control breakpoint>

[DYNAMIC — не кешируется, генерируется per-request]
== Факты о пользователе ==
{json.dumps(facts, sort_keys=True)}

== Релевантные эпизоды ==
{episodes_text}

Сегодняшняя дата: {date}
```

## Инструменты (`agent/tools.py`)

| Инструмент | Когда использует | Реализация |
|---|---|---|
| `save_user_fact` | Пользователь сообщает факт о себе | UPSERT в `user_facts` |
| `get_user_context` | Пользователь спрашивает «что ты знаешь обо мне» | SELECT из `user_facts` |
| `schedule_reminder` | Пользователь просит напомнить | INSERT в `tasks` + APScheduler job |
| `schedule_research` | Пользователь просит исследовать тему | INSERT в `tasks` как ASAP/scheduled |
| `web_search` | Нужна актуальная информация из интернета | `search/tavily.py` |
| `send_telegram_message` | Проактивная отправка (из scheduler jobs) | `bot.send_message(chat_id, text)` |
| `get_recent_conversation` | Контекст последних реплик | SELECT из `conversations` |

Каждый инструмент — отдельная функция в `tools.py`. Список JSON-схем передаётся в `messages.create(tools=...)`.

## Авторизация

Бот отвечает только на сообщения от `TELEGRAM_CHAT_ID` из конфига. Все остальные сообщения игнорируются (middleware).
