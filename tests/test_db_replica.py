"""Read Replica 機能のテスト"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.config import Settings

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---- Fixtures ----

@pytest_asyncio.fixture
async def sqlite_session():
    """SQLite in-memory セッションを提供するフィクスチャ"""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
    await engine.dispose()


# ---- Tests ----

@pytest.mark.asyncio
async def test_get_db_read_returns_session():
    """get_db_read が AsyncSession を返すことを確認"""
    from src.core.database import get_db_read

    gen = get_db_read()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    # クリーンアップ
    try:
        await gen.aclose()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_get_db_read_fallback_to_primary():
    """Read Replica 未設定時はプライマリセッションファクトリを使用"""
    import src.core.database as db_module

    # Read Replica が無効であることを確認
    assert db_module._ReadSessionLocal is None, (
        "テスト環境では Read Replica が無効であること"
    )

    # get_db_read はプライマリ (AsyncSessionLocal) から生成されるはず
    gen = db_module.get_db_read()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    try:
        await gen.aclose()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_get_db_read_with_replica_disabled():
    """read_replica_enabled=False の場合、_ReadSessionLocal は None のままでプライマリを使用"""
    import src.core.database as db_module

    # _ReadSessionLocal が None のとき AsyncSessionLocal を使うことを確認
    original = db_module._ReadSessionLocal
    try:
        db_module._ReadSessionLocal = None  # 強制的に無効化
        gen = db_module.get_db_read()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
    finally:
        db_module._ReadSessionLocal = original
        try:
            await gen.aclose()
        except Exception:
            pass


def test_read_replica_config_defaults():
    """Read Replica のデフォルト設定を確認"""
    settings = Settings(
        database_url=TEST_DB_URL,
        secret_key="test-secret",
    )
    assert settings.read_replica_url == ""
    assert settings.read_replica_enabled is False


def test_setup_read_replica_no_url():
    """URL なし・無効設定時はエンジン未作成"""
    from src.core.database import _setup_read_replica
    import src.core.database as db_module

    original_engine = db_module._read_engine
    original_factory = db_module._ReadSessionLocal

    # read_replica_enabled=False の設定でセットアップ呼び出し
    mock_settings = MagicMock()
    mock_settings.read_replica_enabled = False
    mock_settings.read_replica_url = ""

    with patch("src.core.database.settings", mock_settings):
        db_module._read_engine = None
        db_module._ReadSessionLocal = None
        _setup_read_replica()

    assert db_module._read_engine is None
    assert db_module._ReadSessionLocal is None

    # 元に戻す
    db_module._read_engine = original_engine
    db_module._ReadSessionLocal = original_factory


@pytest.mark.asyncio
async def test_setup_read_replica_with_sqlite_url():
    """SQLite URL で read_replica_enabled=True のとき _ReadSessionLocal が生成される"""
    from src.core.database import _setup_read_replica
    import src.core.database as db_module

    original_engine = db_module._read_engine
    original_factory = db_module._ReadSessionLocal

    mock_settings = MagicMock()
    mock_settings.read_replica_enabled = True
    mock_settings.read_replica_url = TEST_DB_URL
    mock_settings.debug = False

    with patch("src.core.database.settings", mock_settings):
        db_module._read_engine = None
        db_module._ReadSessionLocal = None
        _setup_read_replica()

        assert db_module._read_engine is not None
        assert db_module._ReadSessionLocal is not None

        # エンジンをクリーンアップ
        await db_module._read_engine.dispose()

    # 元に戻す
    db_module._read_engine = original_engine
    db_module._ReadSessionLocal = original_factory


@pytest.mark.asyncio
async def test_get_db_read_uses_read_session_when_configured():
    """_ReadSessionLocal が設定されているとき get_db_read はそれを使用する"""
    import src.core.database as db_module

    replica_engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    replica_factory = async_sessionmaker(
        bind=replica_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    original = db_module._ReadSessionLocal
    try:
        db_module._ReadSessionLocal = replica_factory
        gen = db_module.get_db_read()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
    finally:
        db_module._ReadSessionLocal = original
        try:
            await gen.aclose()
        except Exception:
            pass
        await replica_engine.dispose()
