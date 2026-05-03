# База данных

## Стек

- **PostgreSQL** — основная БД
- **SQLAlchemy 2.x async** — ORM, `AsyncSession` + `asyncpg` driver
- **Alembic** — миграции схемы

## Модели (`db/models.py`)

### `UserFact`
```python
class UserFact(Base):
    __tablename__ = "user_facts"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True)
    value: Mapped[str]
    source_message: Mapped[str | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### `Conversation`
```python
class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str]               # "user" | "assistant"
    content: Mapped[str]
    tool_calls: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime]
    processed_at: Mapped[datetime | None]  # NULL = не вошло в эпизод
```

### `Episode`
```python
class Episode(Base):
    __tablename__ = "episodes"
    id: Mapped[int] = mapped_column(primary_key=True)
    summary: Mapped[str]
    period_start: Mapped[datetime]
    period_end: Mapped[datetime]
    topics: Mapped[list[str]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime]
```

### `Task`
```python
class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_type: Mapped[str]          # "research" | "reminder" | "proactive_check"
    description: Mapped[str]
    status: Mapped[str]             # "pending" | "in_progress" | "done" | "failed"
    result: Mapped[str | None]
    scheduled_at: Mapped[datetime | None]
    apscheduler_job_id: Mapped[str | None]
    created_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
```

### `ProactiveLog`
```python
class ProactiveLog(Base):
    __tablename__ = "proactive_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    trigger: Mapped[str]
    message_sent: Mapped[str]
    sent_at: Mapped[datetime]
```

## Engine и сессии (`db/base.py`)

```python
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

Сессия инжектируется в каждый handler через aiogram middleware.

## Миграции (Alembic)

```bash
# Создать новую миграцию после изменения моделей
uv run alembic revision --autogenerate -m "description"

# Применить миграции
uv run alembic upgrade head

# Откатить последнюю миграцию
uv run alembic downgrade -1
```

`alembic/env.py` настроен на async режим через `run_async_migrations()`.
