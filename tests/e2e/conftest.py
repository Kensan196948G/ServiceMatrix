"""E2Eテスト用フィクスチャ"""
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.core.database import get_db
from src.main import app
from src.models.base import Base

E2E_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def e2e_engine():
    engine = create_async_engine(
        E2E_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_db(e2e_engine):
    async_session = async_sessionmaker(e2e_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def e2e_authed_user(e2e_db: AsyncSession):
    """E2Eテスト用 SystemAdmin ユーザー"""
    from src.models.user import User, UserRole

    now = datetime.now(timezone.utc)
    user = User(
        user_id=uuid.uuid4(),
        username=f"e2e_admin_{uuid.uuid4().hex[:8]}",
        email=f"e2e_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="fakehash",
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    e2e_db.add(user)
    await e2e_db.flush()
    return user


@pytest_asyncio.fixture
async def e2e_auth_headers(e2e_authed_user):
    """SystemAdmin JWT Bearer ヘッダー"""
    from src.core.security import create_access_token

    token = create_access_token(
        {"sub": str(e2e_authed_user.user_id), "role": "SystemAdmin"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def e2e_client(e2e_db: AsyncSession, e2e_auth_headers):
    """E2Eテスト用HTTPクライアント（DB・認証オーバーライド済み）"""

    async def override_get_db():
        yield e2e_db

    app.dependency_overrides[get_db] = override_get_db

    _inc_counter = [0]
    _chg_counter = [0]

    async def mock_inc_number(db):
        _inc_counter[0] += 1
        return f"INC-E2E-{_inc_counter[0]:06d}"

    async def mock_chg_number(db):
        _chg_counter[0] += 1
        return f"CHG-E2E-{_chg_counter[0]:06d}"

    with (
        patch("src.services.incident_service._get_next_incident_number", mock_inc_number),
        patch("src.services.change_service._get_next_change_number", mock_chg_number),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client._e2e_headers = e2e_auth_headers  # type: ignore[attr-defined]
            yield client

    app.dependency_overrides.clear()
