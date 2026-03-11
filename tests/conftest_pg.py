"""PostgreSQL統合テスト用フィクスチャ"""
import os
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.models.base import Base

PG_TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_servicematrix",
)

@pytest_asyncio.fixture(scope="session")
async def pg_engine():
    engine = create_async_engine(PG_TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def pg_session(pg_engine):
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
