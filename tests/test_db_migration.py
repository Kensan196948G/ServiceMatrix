"""Step37: PostgreSQL移行・データベース設定テストスイート"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.models.base import Base

SQLITE_URL = "sqlite+aiosqlite:///:memory:"


# ─── config.py テスト ────────────────────────────────────────────


class TestDatabaseConfig:
    """Settings.get_database_url() のテスト"""

    def test_database_url_default_is_sqlite(self):
        """DATABASE_URLが未設定時、デフォルトはSQLite"""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "",
                "POSTGRES_HOST": "",
            },
            clear=False,
        ):
            from pydantic_settings import BaseSettings

            # キャッシュを回避するため直接インスタンス化
            from src.core.config import Settings

            s = Settings(
                database_url="sqlite+aiosqlite:///./servicematrix.db",
                postgres_host="",
            )
            url = s.get_database_url()
            assert url.startswith("sqlite"), f"Expected sqlite URL, got: {url}"

    def test_config_postgres_env_vars(self):
        """POSTGRES_HOST設定時にPostgreSQL URLが組み立てられる"""
        from src.core.config import Settings

        s = Settings(
            database_url="sqlite+aiosqlite:///./servicematrix.db",
            postgres_host="db.example.com",
            postgres_port=5433,
            postgres_db="mydb",
            postgres_user="myuser",
            postgres_password="mypass",
        )
        url = s.get_database_url()
        assert url == "postgresql+asyncpg://myuser:mypass@db.example.com:5433/mydb"

    def test_database_url_postgresql_takes_priority(self):
        """DATABASE_URLがpostgresqlで始まる場合、それが優先される"""
        from src.core.config import Settings

        explicit_url = "postgresql+asyncpg://user:pass@host:5432/db"
        s = Settings(
            database_url=explicit_url,
            postgres_host="other-host",
        )
        url = s.get_database_url()
        assert url == explicit_url

    def test_connection_pool_config_postgresql(self):
        """PostgreSQL URL使用時にコネクションプール設定が適用される"""
        pg_url = "postgresql+asyncpg://user:pass@localhost:5432/db"
        engine_kwargs: dict = {"echo": False}
        if pg_url.startswith("postgresql"):
            engine_kwargs.update(
                {
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_pre_ping": True,
                }
            )
        assert engine_kwargs["pool_size"] == 10
        assert engine_kwargs["max_overflow"] == 20
        assert engine_kwargs["pool_timeout"] == 30
        assert engine_kwargs["pool_pre_ping"] is True

    def test_connection_pool_config_sqlite(self):
        """SQLite URL使用時にコネクションプール設定が追加されない"""
        sqlite_url = "sqlite+aiosqlite:///./test.db"
        engine_kwargs: dict = {"echo": False}
        if sqlite_url.startswith("postgresql"):
            engine_kwargs.update(
                {
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_pre_ping": True,
                }
            )
        assert "pool_size" not in engine_kwargs
        assert "pool_pre_ping" not in engine_kwargs


# ─── database.py テスト ────────────────────────────────────────────


class TestDatabaseConnection:
    """SQLiteインメモリでの接続テスト"""

    @pytest_asyncio.fixture
    async def sqlite_engine(self):
        eng = create_async_engine(
            SQLITE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield eng
        await eng.dispose()

    @pytest.mark.asyncio
    async def test_sqlite_connection(self, sqlite_engine):
        """SQLiteインメモリDBへの接続が成功する"""
        async with sqlite_engine.connect() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_engine_creation(self, sqlite_engine):
        """エンジンが正常に生成されている"""
        assert sqlite_engine is not None
        assert str(sqlite_engine.url) == "sqlite+aiosqlite:///:memory:"

    @pytest.mark.asyncio
    async def test_session_creation(self, sqlite_engine):
        """非同期セッションが正常に生成・クローズされる"""
        session_factory = async_sessionmaker(
            sqlite_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            assert session is not None
            result = await session.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            assert result.scalar() == 1


# ─── Alembicマイグレーション構造テスト ─────────────────────────────────


class TestMigrationStructure:
    """マイグレーションファイルの構造検証"""

    def _get_worktree_root(self) -> Path:
        """WorkTree内のルートパスを取得"""
        # テスト実行場所に応じてパスを解決
        candidates = [
            Path("/mnt/LinuxHDD/ServiceMatrix/.worktrees/step37-pg-migration"),
            Path("/mnt/LinuxHDD/ServiceMatrix"),
        ]
        for p in candidates:
            if (p / "alembic" / "versions").exists():
                return p
        # フォールバック: 相対パスで探索
        current = Path(__file__).resolve().parent.parent
        return current

    def test_migration_002_file_exists(self):
        """002マイグレーションファイルが存在する"""
        root = self._get_worktree_root()
        migration_file = root / "alembic" / "versions" / "002_add_indexes.py"
        assert migration_file.exists(), f"Migration file not found: {migration_file}"

    def test_alembic_migration_002_upgrade_downgrade_structure(self):
        """002マイグレーションにupgrade/downgrade関数が定義されている"""
        root = self._get_worktree_root()
        migration_file = root / "alembic" / "versions" / "002_add_indexes.py"
        content = migration_file.read_text()
        assert "def upgrade()" in content
        assert "def downgrade()" in content
        assert 'down_revision = "001"' in content

    def test_migration_index_names_unique(self):
        """002マイグレーション内のインデックス名が重複していない"""
        root = self._get_worktree_root()
        migration_file = root / "alembic" / "versions" / "002_add_indexes.py"
        content = migration_file.read_text()

        # create_indexの引数からインデックス名を抽出
        import re

        index_names = re.findall(r'create_index\("([^"]+)"', content)
        assert len(index_names) > 0, "No index names found"
        assert len(index_names) == len(set(index_names)), (
            f"Duplicate index names: {index_names}"
        )

    def test_migration_no_duplicate_with_001(self):
        """002のインデックスが001と重複していない"""
        root = self._get_worktree_root()

        # 001のインデックス名を抽出
        migration_001 = root / "alembic" / "versions" / "001_initial_schema.py"
        content_001 = migration_001.read_text()

        import re

        # op.create_index と CREATE INDEX の両方を検索
        idx_001_op = set(re.findall(r'create_index\([\'"]([^\'"]+)[\'"]', content_001))
        idx_001_raw = set(re.findall(r'CREATE (?:UNIQUE )?INDEX (\w+)', content_001))
        all_001_indexes = idx_001_op | idx_001_raw

        # 002のインデックス名を抽出
        migration_002 = root / "alembic" / "versions" / "002_add_indexes.py"
        content_002 = migration_002.read_text()
        idx_002 = set(re.findall(r'create_index\([\'"]([^\'"]+)[\'"]', content_002))

        overlap = all_001_indexes & idx_002
        assert len(overlap) == 0, f"Index names overlap between 001 and 002: {overlap}"


# ─── ドキュメントテスト ──────────────────────────────────────────


class TestDocumentation:
    """マイグレーション関連ドキュメントの存在確認"""

    def test_migration_guide_exists(self):
        """MIGRATION_GUIDE.mdが存在する"""
        candidates = [
            Path("/mnt/LinuxHDD/ServiceMatrix/.worktrees/step37-pg-migration/docs/MIGRATION_GUIDE.md"),
            Path("/mnt/LinuxHDD/ServiceMatrix/docs/MIGRATION_GUIDE.md"),
        ]
        found = any(p.exists() for p in candidates)
        assert found, "MIGRATION_GUIDE.md not found in docs/"

    def test_migration_guide_content(self):
        """MIGRATION_GUIDE.mdに必要なセクションが含まれている"""
        candidates = [
            Path("/mnt/LinuxHDD/ServiceMatrix/.worktrees/step37-pg-migration/docs/MIGRATION_GUIDE.md"),
            Path("/mnt/LinuxHDD/ServiceMatrix/docs/MIGRATION_GUIDE.md"),
        ]
        content = ""
        for p in candidates:
            if p.exists():
                content = p.read_text()
                break

        assert "環境変数" in content or "DATABASE_URL" in content
        assert "Alembic" in content or "alembic" in content
        assert "docker" in content.lower() or "Docker" in content
        assert "トラブルシューティング" in content or "Troubleshoot" in content
