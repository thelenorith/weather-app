"""Database connection management.

Provides async database connection using SQLAlchemy with asyncpg.

## Configuration

Database connection is configured via environment variables:
- DATABASE_URL: Full PostgreSQL connection string
- DATABASE_POOL_SIZE: Connection pool size (default: 5)
- DATABASE_MAX_OVERFLOW: Max overflow connections (default: 10)

## SSL/TLS

For production, use SSL connections:
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

## Usage

```python
from weather_events.database import get_db, init_db

# Initialize on startup
await init_db()

# Use in request handlers
async with get_db() as session:
    user = await session.get(User, user_id)
```
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from weather_events.config import get_settings
from weather_events.database.models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Initialize the database connection.

    Creates the async engine and session factory. Should be called
    once on application startup.
    """
    global _engine, _session_factory

    settings = get_settings()

    logger.info("Initializing database connection")

    # Create async engine
    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,  # Verify connections before use
        echo=settings.database_echo,  # Log SQL in debug mode
    )

    # Create session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Database connection initialized")


async def close_db() -> None:
    """Close the database connection.

    Should be called on application shutdown.
    """
    global _engine, _session_factory

    if _engine:
        logger.info("Closing database connection")
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def create_tables() -> None:
    """Create all database tables.

    For development/testing only. Use Alembic migrations in production.
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created")


async def drop_tables() -> None:
    """Drop all database tables.

    For development/testing only. Use with caution!
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    logger.warning("Database tables dropped")


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session.

    Use as an async context manager:
    ```python
    async with get_db() as session:
        # Use session
        await session.commit()
    ```

    The session is automatically closed when the context exits.
    Transactions are not automatically committed - call commit() explicitly.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = _session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Type alias for dependency injection
DatabaseSession = AsyncSession


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Usage:
    ```python
    @app.get("/users/{user_id}")
    async def get_user(
        user_id: UUID,
        db: AsyncSession = Depends(get_db_session)
    ):
        user = await db.get(User, user_id)
        return user
    ```
    """
    async with get_db() as session:
        yield session
