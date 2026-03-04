"""SQLAlchemy async エンジン・セッション管理"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

_db_url = settings.get_database_url()

# PostgreSQL用コネクションプール設定（SQLite使用時は無視）
_engine_kwargs: dict = {"echo": settings.debug}
if _db_url.startswith("postgresql"):
    _engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_pre_ping": True,
        }
    )

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依存性注入用DBセッションジェネレータ"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
