import json
from datetime import datetime, timezone

from profitist.memory.store import ContextBundle

SYSTEM_PREFIX = """\
Ты — персональный ИИ-ассистент пользователя. Ты помнишь факты о нём, ведёшь долгосрочный контекст и можешь действовать проактивно.

Правила:
- Отвечай на русском, если пользователь пишет на русском. Переключайся на язык пользователя.
- Если пользователь сообщает факт о себе — вызови save_user_fact.
- Если просит напомнить — вызови schedule_reminder с точной датой/временем.
- Если просит исследовать тему — вызови schedule_research (если нужно позже) или web_search (если нужно сейчас).
- Не придумывай факты о пользователе. Используй только то, что знаешь из контекста.
- Будь кратким и по делу, но дружелюбным."""


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

    now = datetime.now(timezone.utc)
    lines.append(f"\nСегодня: {now:%Y-%m-%d %H:%M} UTC")

    return "\n".join(lines)


def build_messages(context: ContextBundle, user_message: str) -> list[dict]:
    messages: list[dict] = []
    for turn in context.recent:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user_message})
    return messages
