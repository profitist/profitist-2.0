import logging

from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from profitist.agent.loop import run_agent_loop
from profitist.memory.store import add_conversation_turn

logger = logging.getLogger(__name__)

router = Router(name="main")


@router.message()
async def handle_message(message: Message, db: AsyncSession, scheduler) -> None:
    if not message.text:
        return

    user_text = message.text

    # 1. Save user message
    await add_conversation_turn(db, role="user", content=user_text)

    # 3. Run agent
    reply = await run_agent_loop(
        user_message=user_text,
        session=db,
        scheduler=scheduler,
    )

    # 4. Send reply
    await message.answer(reply)

    # 5. Save assistant reply
    await add_conversation_turn(db, role="assistant", content=reply)
