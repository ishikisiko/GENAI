from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession


class Database:
    """Shared async DB connection/session wrapper."""

    def __init__(self, database_url: str) -> None:
        self.url = database_url
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            future=True,
            echo=False,
        )
        self._session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def ping(self) -> None:
        """Validate database connectivity."""
        async with self.session() as session:
            await session.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self.engine.dispose()
