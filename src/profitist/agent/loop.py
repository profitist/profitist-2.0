import json
import logging

import openai
from sqlalchemy.ext.asyncio import AsyncSession

from profitist.agent.prompts import build_messages, build_system_prompt
from profitist.agent.router import classify_intent, get_model_for_intent
from profitist.agent.tools import TOOL_DEFINITIONS, execute_tool
from profitist.config import settings
from profitist.memory.store import build_context

logger = logging.getLogger(__name__)

_client = openai.AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.api_base_url,
)

MAX_TOOL_ROUNDS = 10


async def run_agent_loop(
    user_message: str,
    session: AsyncSession,
    scheduler=None,
    query_topics: list[str] | None = None,
    model_override: str | None = None,
) -> str:
    intent = await classify_intent(user_message)
    model = model_override or get_model_for_intent(intent)
    logger.info("Intent: %s → model: %s", intent, model)

    context = await build_context(
        session,
        query_topics=query_topics or [],
        working_memory_turns=settings.max_working_memory_turns,
        max_episodes=settings.max_relevant_episodes,
    )

    system = build_system_prompt(context)
    messages = [{"role": "system", "content": system}] + build_messages(context, user_message)

    text = ""
    for _ in range(MAX_TOOL_ROUNDS):
        response = await _client.chat.completions.create(
            model=model,
            max_tokens=4096,
            temperature=0.9,
            top_p=0.95,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        msg = response.choices[0].message
        text = msg.content or ""
        tool_calls = msg.tool_calls or []

        if response.choices[0].finish_reason == "stop" or not tool_calls:
            return text

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            logger.info("Executing tool: %s(%s)", tc.function.name, tc.function.arguments)
            result = await execute_tool(
                name=tc.function.name,
                input_data=json.loads(tc.function.arguments),
                session=session,
                scheduler=scheduler,
                user_message=user_message,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return text if text else "Достигнут лимит вызовов инструментов."
