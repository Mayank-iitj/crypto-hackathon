"""
Q-Shield Database Module
Async SQLAlchemy setup with connection pooling.
"""

from datetime import datetime, timezone
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import QueuePool

from app.core.config import settings


# Naming convention for constraints
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    metadata = metadata
    
    # Common columns
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class DatabaseManager:
    """
    Manages database connections with proper lifecycle management.
    """
    
    _engine: AsyncEngine = None
    _session_factory: async_sessionmaker[AsyncSession] = None
    
    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """Get or create the database engine."""
        if cls._engine is None:
            # Convert sync URL to async
            db_url = settings.DATABASE_URL
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            
            cls._engine = create_async_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                pool_pre_ping=True,
                echo=settings.DATABASE_ECHO,
            )
            
            # Add connection event listeners
            @event.listens_for(cls._engine.sync_engine, "connect")
            def set_connection_options(dbapi_conn, connection_record):
                """Set connection-level options."""
                # Enable statement timeout (30 seconds)
                cursor = dbapi_conn.cursor()
                cursor.execute("SET statement_timeout = '30s'")
                cursor.close()
        
        return cls._engine
    
    @classmethod
    def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        """Get or create the session factory."""
        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                bind=cls.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        return cls._session_factory
    
    @classmethod
    async def close(cls):
        """Close all database connections."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    Usage:
        async with get_session_context() as session:
            result = await session.execute(query)
    """
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize the database, creating tables if needed."""
    engine = DatabaseManager.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database():
    """Close database connections."""
    await DatabaseManager.close()
