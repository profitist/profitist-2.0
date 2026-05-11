import openai

from profitist.config import settings

_client = openai.AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.api_base_url,
)

INTENT_MODEL_MAP = {
    "memory": settings.main_model,
    "schedule": settings.main_model,
    "chat": settings.main_model,
    "research": settings.main_model,
}

_CLASSIFY_PROMPT = """\
Classify the user message intent into exactly one category.
Categories:
- memory: user wants to save/recall a personal fact (e.g. "запомни", "что ты знаешь обо мне")
- schedule: user wants to set a reminder or schedule a task (e.g. "напомни", "через 2 дня")
- research: user wants information lookup or deep analysis (e.g. "исследуй", "найди", "что происходит с")
- chat: general conversation, questions, requests

Respond with a single word: memory, schedule, research, or chat."""


async def classify_intent(message: str) -> str:
    response = await _client.chat.completions.create(
        model=settings.fast_model,
        max_tokens=10,
        temperature=0,
        messages=[
            {"role": "system", "content": _CLASSIFY_PROMPT},
            {"role": "user", "content": message},
        ],
    )
    intent = response.choices[0].message.content.strip().lower()
    if intent not in INTENT_MODEL_MAP:
        return "chat"
    return intent


def get_model_for_intent(intent: str) -> str:
    return INTENT_MODEL_MAP.get(intent, settings.main_model)
