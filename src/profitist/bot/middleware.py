import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from profitist.config import settings
from profitist.db.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Пропускает только сообщения от авторизованного chat_id."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.chat.id != settings.telegram_chat_id:
            logger.warning("Unauthorized chat_id: %s", event.chat.id)
            return None
        return await handler(event, data)


class DbSessionMiddleware(BaseMiddleware):
    """Инжектирует AsyncSession в handler через data['db']."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["db"] = session
            return await handler(event, data)
