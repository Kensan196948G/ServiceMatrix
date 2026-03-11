"""SQLAlchemy async エンジン・セッション管理"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

# SQLite は pool_size/max_overflow 非対応
_is_postgres = settings.database_url.startswith("postgresql")
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    **(
        {
            "pool_size": 20,
            "max_overflow": 40,
            "pool_recycle": 3600,
        }
        if _is_postgres
        else {}
    ),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Read Replica エンジン（設定されている場合のみ）
_read_engine = None
_ReadSessionLocal = None


def _setup_read_replica():
    """Read Replica エンジンをセットアップ（設定がある場合のみ）"""
    global _read_engine, _ReadSessionLocal
    if settings.read_replica_enabled and settings.read_replica_url:
        _read_engine = create_async_engine(
            settings.read_replica_url,
            echo=settings.debug,
            pool_pre_ping=True,
            **(
                {
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_recycle": 3600,
                }
                if settings.read_replica_url.startswith("postgresql")
                else {}
            ),
        )
        _ReadSessionLocal = async_sessionmaker(
            bind=_read_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )


_setup_read_replica()


async def get_db_read() -> AsyncGenerator[AsyncSession, None]:
    """
    Read Replica 用セッション（読み取り専用クエリ向け）。
    Read Replica が設定されていない場合はプライマリを使用。
    FastAPI依存性注入用。
    """
    session_factory = _ReadSessionLocal if _ReadSessionLocal else AsyncSessionLocal
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
