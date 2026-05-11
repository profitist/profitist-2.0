import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from profitist.config import settings
from profitist.memory.store import ContextBundle

SYSTEM_PREFIX = """\
Ты — персональный ИИ-ассистент пользователя. Ты помнишь факты о нём, ведёшь долгосрочный контекст и можешь действовать проактивно.

Стиль:
- Пиши живо и по-человечески. Варьируй формулировки — не используй одни и те же фразы-зачины («Хорошо», «Конечно») в каждом ответе.
- Отвечай на языке пользователя. По умолчанию — русский.
- Длина ответа — по ситуации: короткий вопрос → короткий ответ, содержательная просьба → развернутый ответ.

Инструменты:
- Пользователь сообщает факт о себе → save_user_fact.
- Просьба напомнить / запланировать → schedule_reminder с точным ISO 8601 (с offset, например 2026-05-11T18:00:00+05:00).
- Исследование темы → schedule_research (если нужно позже) или web_search (если нужно сейчас).

Правила:
- Не выдумывай факты о пользователе. Только то, что в контексте.
- Все времена интерпретируй в таймзоне пользователя (указана ниже). При создании напоминания ВСЕГДА передавай scheduled_at с UTC-offset."""


def build_system_prompt(context: ContextBundle) -> str:
    lines: list[str] = [SYSTEM_PREFIX]

    if context.facts:
        facts_dict = {f.key: f.value for f in context.facts}
        lines.append("\n== Известные факты о пользователе ==")
        lines.append(json.dumps(facts_dict, ensure_ascii=False, sort_keys=True, indent=2))

    if context.episodes:
        lines.append("\n== Релевантные эпизоды из прошлых разговоров ==")
        for ep in context.episodes:
            period = f"{ep.period_start:%Y-%m-%d} — {ep.period_end:%Y-%m-%d}"
            lines.append(f"[{period}] {ep.summary}")

    tz = ZoneInfo(settings.user_timezone)
    now = datetime.now(timezone.utc).astimezone(tz)
    offset_hours = int(now.utcoffset().total_seconds() // 3600)
    offset_str = f"UTC+{offset_hours}" if offset_hours >= 0 else f"UTC{offset_hours}"
    lines.append(
        f"\nТаймзона пользователя: {settings.user_timezone} ({offset_str}). "
        f"Сейчас: {now:%Y-%m-%d %H:%M}. "
        f"При schedule_reminder передавай offset, например {now:%Y-%m-%dT%H:%M:%S}{now:%z}."
    )

    return "\n".join(lines)


def build_messages(context: ContextBundle, user_message: str) -> list[dict]:
    messages: list[dict] = []
    for turn in context.recent:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user_message})
    return messages
