# Database setup (async) — complete reference

This file documents the asynchronous SQLAlchemy / SQLModel database setup used in this project. It contains:

- The original code snippet
- Detailed explanation of every line and configuration option
- A safe `init_db()` implementation and how to wire it into FastAPI startup
- Alembic notes + small async-compatible env.py snippet
- Example FastAPI route using the session dependency
- Example pytest `conftest.py` fixture for tests
- Tips for pgvector (CREATE EXTENSION) and production recommendations
- Troubleshooting checklist

---

## Original code

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from sqlalchemy import text
from sqlmodel import SQLModel

engine=create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

# async def init_db():
#     async with engine.begin() as conn:
#         await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
#         await conn.run_sync(SQLModel.metadata.create_all)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 1 — High-level overview

- `create_async_engine(...)` sets up an asynchronous SQLAlchemy engine (for example, using `asyncpg` with PostgreSQL).
- `async_sessionmaker(...)` creates a factory to produce `AsyncSession` instances used to interact with the DB.
- `get_session()` is an async dependency (generator) used by FastAPI to provide a session per request.
- The commented `init_db()` shows a pattern to create required DB extensions and create tables from `SQLModel` metadata — useful in development but in production prefer migrations (Alembic).

---

## 2 — settings.DATABASE_URL

- Must be an async DB URL when using async drivers. Example (Postgres + asyncpg):
  - `postgresql+asyncpg://user:password@host:port/dbname`
- Load from environment (e.g., via pydantic `settings` object in `app.config`).
- Keep credentials out of source control.

---

## 3 — create_async_engine parameters explained

- `settings.DATABASE_URL` — the connection string.
- `pool_pre_ping=True` — when True, SQLAlchemy checks a connection before using it; helps avoid using dead/stale connections.
- `echo=False` — controls SQL logging. Set to True for debugging; keep False in production to avoid log noise and accidental exposure of SQL.

Other optional params:
- `future=True` — (SQLAlchemy 1.4+) can be passed to use 2.0-style behaviors; not required here if using 1.4+ default behavior.
- Connection pooling params (tune based on your workload and DB provider):
  - `pool_size`, `max_overflow`, `pool_timeout` (only for sync DBAPI pools; for async drivers these behave differently).

---

## 4 — async_sessionmaker configuration

- `bind=engine` — sessions will use this engine.
- `class_=AsyncSession` — ensures session instances are async-capable.
- `autoflush=False` — prevents automatic flush before queries. When False, you explicitly control when to flush (recommended for clear behavior).
- `expire_on_commit=False` — prevents objects from being expired on commit, which avoids lazy reload errors after the session is closed. Often desirable in web APIs when returning models after commit.

Choose behavior based on your return pattern:
- If you return ORM instances directly (and serialize them via Pydantic), prefer `expire_on_commit=False`.
- If you want stricter identity/consistency, use `expire_on_commit=True` with explicit refresh.

---

## 5 — get_session() dependency — patterns

Current minimal pattern (yields session, caller controls commits):

```python
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

Pattern that manages commit/rollback automatically per-request:

```python
from typing import AsyncGenerator

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Notes:
- Automatic commit/rollback in the dependency is convenient but can be limiting if you need multi-step transactions inside services.
- Prefer explicit transaction management in services for more control, or use the dependency-managed pattern if your endpoints are simple.

---

## 6 — The commented `init_db()` block explained

Original commented code:

```python
# async def init_db():
#     async with engine.begin() as conn:
#         await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
#         await conn.run_sync(SQLModel.metadata.create_all)
```

Line-by-line:
- `async with engine.begin() as conn:` — opens an async connection and begins a transaction context.
- `await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))` — runs raw SQL to create the `vector` extension (pgvector) if it's not present. Important:
  - Installing extensions requires appropriate privileges; many managed DBs require superuser or DBA to enable extensions.
  - For production, extension installation is often done by an operator or through DB provisioning scripts.
- `await conn.run_sync(SQLModel.metadata.create_all)` — `create_all()` is synchronous; `run_sync()` runs a synchronous callable using the same DB connection. This call will create table schemas defined in your SQLModel models if they don't already exist.

Caveats:
- `metadata.create_all()` is fine for development and simple setups, but for production you should use Alembic migrations for schema evolution and reproducibility.
- Avoid calling `create_all()` concurrently from multiple app instances (race conditions). Run as a single migration step.

---

## 7 — Safe `init_db()` implementation (development use)

```python
from sqlalchemy import text
from sqlmodel import SQLModel

async def init_db(skip_extension=False):
    """
    Creates required extensions (pgvector) and creates tables from SQLModel metadata.

    skip_extension: set True if the DB already has the extension, or if you cannot run CREATE EXTENSION.
    """
    async with engine.begin() as conn:
        if not skip_extension:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception:
                # Log and continue; extension creation may require superuser.
                # In production, prefer to create extensions outside application runtime.
                pass
        # Run the synchronous create_all inside the async connection
        await conn.run_sync(SQLModel.metadata.create_all)
```

How to wire into FastAPI startup (development only):

```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    # call init_db() in startup; consider using environment flag to only run in dev
    await init_db(skip_extension=True)  # skip_extension if you can't create extensions from app
```

---

## 8 — Example FastAPI route using AsyncSession

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from app.db import get_session  # the dependency
from app.models.note import Note, NoteCreate
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/notes", response_model=Note)
async def create_note(payload: NoteCreate, session: AsyncSession = Depends(get_session)):
    note = Note.from_orm(payload)
    session.add(note)
    await session.flush()        # sends insert to DB and populates PK
    await session.refresh(note)  # ensure instance has DB state if needed
    # commit depends on your dependency pattern; commit here if not auto-committed
    # await session.commit()
    return note
```

Important patterns:
- `await session.flush()` — pushes pending changes so you can access generated primary keys.
- `await session.refresh(instance)` — ensures the instance is populated from DB after commit/flush.
- Manage transactions explicitly or rely on dependency-managed commit.

---

## 9 — Alembic + async usage (recommended for production)

- Use Alembic for migrations, not `metadata.create_all()` in production.
- Typical strategy:
  - Keep async app code for runtime.
  - Use Alembic with a *sync* migration connection to run migrations (easier), or adapt Alembic's env.py to call async run_sync if you want to use the same async URL.

Example minimal `alembic/env.py` snippet for using a sync URL during migrations:

```python
# In alembic.ini or env, provide a sync DATABASE_URL for migrations:
# e.g., postgresql://user:pass@host:port/dbname  (no +asyncpg)
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import *  # ensure metadata is imported

# this is the Alembic Config object, which provides access to the values within the .ini file
config = context.config

fileConfig(config.config_file_name)
target_metadata = SQLModel.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Notes:
- For local dev you can set a separate `alembic` connection URL that uses the sync driver (`psycopg2`) while the app uses `asyncpg`.
- If you want to run Alembic with the async engine, see Alembic docs and use `await connection.run_sync` pattern in env.py.

---

## 10 — Test fixture example (tests/conftest.py)

Example to create a test DB and override get_session dependency:

```python
import asyncio
import pytest
from httpx import AsyncClient
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.config import settings

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"

@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function", autouse=True)
async def prepare_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest.fixture()
async def session(engine):
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s

@pytest.fixture()
async def client(session, monkeypatch):
    # override get_session to return our test session
    async def _get_session_override():
        async with session as s:
            yield s

    monkeypatch.setattr("app.db.get_session", _get_session_override)
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
```

Notes:
- For test isolation, create/drop schema per test function or use transactional rollbacks.
- Alternatively, use a Docker-managed ephemeral Postgres for tests.

---

## 11 — pgvector / CREATE EXTENSION notes

- `CREATE EXTENSION vector;` installs pgvector on the database server.
- Many managed DB services (RDS, Cloud SQL, etc.) may require enabling pgvector via provider UI or a privileged user.
- If you cannot run `CREATE EXTENSION` from the app, run it once manually or via infrastructure provisioning scripts.
- After installing pgvector, add indices appropriate to your search volume (e.g., `CREATE INDEX ON notes USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);`), and run `ANALYZE` as needed.

---

## 12 — Troubleshooting checklist

- Connection URL wrong or missing `+asyncpg` -> use `postgresql+asyncpg://...`
- Permission denied on `CREATE EXTENSION` -> run manually or ask DBA.
- Tests fail due to missing tables -> ensure test setup creates schema or run migrations.
- Getting "Instance has been expired" errors after commit -> set `expire_on_commit=False` or adjust access pattern.
- Long-running transactions -> ensure sessions are closed promptly and avoid long blocking operations inside DB transactions.
- SQL not logged -> set `echo=True` for debugging, or configure logging for SQLAlchemy.

---

## 13 — Security & production recommendations

- Use Alembic for schema migrations.
- Do not run `metadata.create_all()` in production — rely on migrations.
- Protect DB credentials, use secrets manager or environment variables injected at runtime.
- Monitor DB connection pool usage and tune pool sizes for your environment.
- Keep `echo=False` in production to reduce log noise and avoid exposing queries.

---

## 14 — Quick reference snippets

- Minimal dependency:

```python
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

- Auto-commit dependency:

```python
async def get_session_auto_commit():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
```

- Call `init_db()` only in dev or CI environment, and prefer migrations in prod.

---

If you want, I can:
- Commit this file (DB_SETUP.md) to your repository,
- Add the `init_db()` implementation into `app/db.py` and wire it into `app.main` startup,
- Generate an Alembic `env.py` fully tailored to your repository and SQLModel models,
- Create `tests/conftest.py` in your repo with the fixture above.

Tell me which of those to do next and I will apply it.