# Telegram бот

## Стек

**aiogram 3.x** — async-native, Router/Middleware архитектура.

## Авторизация

Бот работает только для одного пользователя. Все входящие сообщения проверяются через middleware: если `message.chat.id != settings.telegram_chat_id` — игнорируются.

## Middleware (`bot/middleware.py`)

`DbSessionMiddleware` — инжектирует `AsyncSession` в каждый handler через `data["db"]`. Сессия открывается на время обработки одного сообщения и закрывается после.

```python
class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with AsyncSessionLocal() as session:
            data["db"] = session
            return await handler(event, data)
```

## Handler (`bot/router.py`)

Один универсальный handler на все текстовые сообщения:

```
handle_message(message, db)
  1. Сохранить сообщение пользователя в conversations
  2. Отправить typing action (пока агент думает)
  3. classify_intent(message.text) → выбрать модель
  4. build_context(message.text, db)
  5. run_agent_loop(message.text, context, model, db, bot, chat_id)
  6. Отправить ответ пользователю
  7. Сохранить ответ агента в conversations
```

## Проактивная отправка

Scheduler jobs отправляют сообщения напрямую через `bot.send_message(chat_id, text)`. Экземпляр `Bot` передаётся в job-функции при регистрации в `main.py`.
