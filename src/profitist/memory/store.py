from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from profitist.db.models import Conversation, Episode, ProactiveLog, Task, UserFact


# --- Context bundle ---


@dataclass
class ContextBundle:
    facts: list[UserFact]
    recent: list[Conversation]
    episodes: list[Episode]


# --- User facts ---


async def upsert_user_fact(
    session: AsyncSession,
    key: str,
    value: str,
    source_message: str | None = None,
) -> UserFact:
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(UserFact)
        .values(key=key, value=value, source_message=source_message, created_at=now, updated_at=now)
        .on_conflict_do_update(
            index_elements=["key"],
            set_={"value": value, "source_message": source_message, "updated_at": now},
        )
        .returning(UserFact)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def get_all_user_facts(session: AsyncSession) -> list[UserFact]:
    result = await session.execute(select(UserFact).order_by(UserFact.key))
    return list(result.scalars().all())


async def delete_user_fact(session: AsyncSession, key: str) -> bool:
    fact = await session.execute(select(UserFact).where(UserFact.key == key))
    obj = fact.scalar_one_or_none()
    if obj is None:
        return False
    await session.delete(obj)
    await session.commit()
    return True


# --- Conversations ---


async def add_conversation_turn(
    session: AsyncSession,
    role: str,
    content: str,
    tool_calls: dict | None = None,
) -> Conversation:
    turn = Conversation(role=role, content=content, tool_calls=tool_calls)
    session.add(turn)
    await session.commit()
    return turn


async def get_recent_conversations(session: AsyncSession, limit: int = 8) -> list[Conversation]:
    result = await session.execute(
        select(Conversation).order_by(Conversation.id.desc()).limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def get_unprocessed_conversations(
    session: AsyncSession,
    older_than_hours: int = 24,
    min_count: int = 10,
) -> list[Conversation]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    result = await session.execute(
        select(Conversation)
        .where(Conversation.processed_at.is_(None), Conversation.created_at < cutoff)
        .order_by(Conversation.id)
    )
    rows = list(result.scalars().all())
    return rows if len(rows) >= min_count else []


async def mark_conversations_processed(session: AsyncSession, ids: list[int]) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.execute(
        update(Conversation)
        .where(Conversation.id.in_(ids))
        .values(processed_at=now)
    )
    await session.commit()


# --- Episodes ---


async def save_episode(
    session: AsyncSession,
    summary: str,
    period_start: datetime,
    period_end: datetime,
    topics: list[str],
) -> Episode:
    episode = Episode(
        summary=summary,
        period_start=period_start,
        period_end=period_end,
        topics=topics,
    )
    session.add(episode)
    await session.commit()
    return episode


async def get_relevant_episodes(
    session: AsyncSession,
    query_topics: list[str],
    limit: int = 3,
) -> list[Episode]:
    if not query_topics:
        result = await session.execute(
            select(Episode).order_by(Episode.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    result = await session.execute(
        select(Episode)
        .where(Episode.topics.overlap(query_topics))
        .order_by(Episode.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# --- Tasks ---


async def create_task(
    session: AsyncSession,
    task_type: str,
    description: str,
    scheduled_at: datetime | None = None,
    apscheduler_job_id: str | None = None,
) -> Task:
    task = Task(
        task_type=task_type,
        description=description,
        status="pending",
        scheduled_at=scheduled_at,
        apscheduler_job_id=apscheduler_job_id,
    )
    session.add(task)
    await session.commit()
    return task


async def update_task_status(
    session: AsyncSession,
    task_id: int,
    status: str,
    result: str | None = None,
) -> None:
    values: dict = {"status": status}
    if status in ("done", "failed"):
        values["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    if result is not None:
        values["result"] = result
    await session.execute(update(Task).where(Task.id == task_id).values(**values))
    await session.commit()


async def get_task(session: AsyncSession, task_id: int) -> Task | None:
    result = await session.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_pending_tasks(session: AsyncSession) -> list[Task]:
    result = await session.execute(
        select(Task).where(Task.status == "pending").order_by(Task.created_at)
    )
    return list(result.scalars().all())


# --- Proactive log ---


async def log_proactive_message(
    session: AsyncSession,
    trigger: str,
    message_sent: str,
) -> ProactiveLog:
    log = ProactiveLog(trigger=trigger, message_sent=message_sent)
    session.add(log)
    await session.commit()
    return log


# --- Context builder ---


async def build_context(
    session: AsyncSession,
    query_topics: list[str],
    working_memory_turns: int = 8,
    max_episodes: int = 3,
) -> ContextBundle:
    facts = await get_all_user_facts(session)
    recent = await get_recent_conversations(session, limit=working_memory_turns)
    episodes = await get_relevant_episodes(session, query_topics=query_topics, limit=max_episodes)
    return ContextBundle(facts=facts, recent=recent, episodes=episodes)
