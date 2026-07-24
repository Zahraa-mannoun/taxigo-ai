"""
Database engine and session configuration.

Uses SQLAlchemy 2.0 async engine with asyncpg driver against PostgreSQL.
The engine uses a connection pool sized for a small single-driver dispatch
service; adjust pool_size/max_overflow if scaling to multiple drivers.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/taxigo",
)

# Railway/Heroku-style URLs sometimes come as postgres:// or postgresql://
# without the asyncpg driver suffix -- normalize so asyncpg is always used.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def get_db():
    """FastAPI dependency that yields a scoped async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def db_session():
    """Context manager for use outside of FastAPI's DI system (background tasks)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create tables if they do not already exist (idempotent bootstrap).

    Production deployments should also run `alembic upgrade head` for
    proper migration tracking; this call is a safety net so the app
    works out of the box on a fresh database.
    """
    from models import Booking  # noqa: F401  (ensures model is registered on Base)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection() -> bool:
    """Used by the /health endpoint to verify DB connectivity."""
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
