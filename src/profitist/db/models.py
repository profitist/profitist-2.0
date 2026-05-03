from datetime import datetime

from sqlalchemy import ARRAY, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from profitist.db.base import Base


class UserFact(Base):
    __tablename__ = "user_facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True, index=True)
    value: Mapped[str]
    source_message: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str]
    content: Mapped[str]
    tool_calls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    summary: Mapped[str]
    period_start: Mapped[datetime]
    period_end: Mapped[datetime]
    topics: Mapped[list[str]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_type: Mapped[str]
    description: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending")
    result: Mapped[str | None]
    scheduled_at: Mapped[datetime | None]
    apscheduler_job_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None]


class ProactiveLog(Base):
    __tablename__ = "proactive_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    trigger: Mapped[str]
    message_sent: Mapped[str]
    sent_at: Mapped[datetime] = mapped_column(server_default=func.now())
