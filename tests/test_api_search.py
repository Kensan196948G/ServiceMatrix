"""グローバル検索 API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def authed_user(db_session):
    """ユニークメールの SystemAdmin ユーザー"""
    from src.models.user import User, UserRole
    uid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    user = User(
        user_id=uid,
        username=f"search_admin_{uid.hex[:8]}",
        email=f"search_{uid.hex[:8]}@test.com",
        hashed_password="fakehash",
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(authed_user):
    from src.core.security import create_access_token
    token = create_access_token({"sub": str(authed_user.user_id), "role": "SystemAdmin"})
    return {"Authorization": f"Bearer {token}"}

BASE = "/api/v1/search"


async def test_search_returns_structure(client, auth_headers):
    """GET /search?q=test → 200, query/total/results 構造"""
    resp = await client.get(f"{BASE}?q=test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "total" in data
    assert "results" in data
    assert data["query"] == "test"


async def test_search_includes_all_types(client, auth_headers):
    """デフォルト検索 → incidents/problems/changes/cmdb キーが含まれる"""
    resp = await client.get(f"{BASE}?q=ab", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert "incidents" in results
    assert "problems" in results
    assert "changes" in results
    assert "cmdb" in results


async def test_search_with_type_filter(client, auth_headers):
    """types=incidents → incidents のみ返る"""
    resp = await client.get(f"{BASE}?q=test&types=incidents", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert "incidents" in results
    assert "problems" not in results


async def test_search_with_multiple_types(client, auth_headers):
    """types=incidents,changes → 2種類のみ返る"""
    resp = await client.get(f"{BASE}?q=test&types=incidents,changes", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert "incidents" in results
    assert "changes" in results
    assert "problems" not in results


async def test_search_missing_query(client, auth_headers):
    """q パラメータなし → 422"""
    resp = await client.get(BASE, headers=auth_headers)
    assert resp.status_code == 422


async def test_search_query_too_short(client, auth_headers):
    """q が1文字 → 422 (min_length=2)"""
    resp = await client.get(f"{BASE}?q=a", headers=auth_headers)
    assert resp.status_code == 422


async def test_search_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(f"{BASE}?q=test")
    assert resp.status_code == 401


async def test_search_with_limit(client, auth_headers):
    """limit パラメータ → 200"""
    resp = await client.get(f"{BASE}?q=test&limit=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["query"] == "test"


async def test_search_finds_created_incident(client, auth_headers):
    """インシデント作成後に検索でヒットする"""
    from unittest.mock import patch

    async def _mock_next(db):
        return "INC-SRCH-000001"

    with patch("src.services.incident_service._get_next_incident_number", _mock_next):
        await client.post(
            "/api/v1/incidents",
            json={"title": "unique_search_keyword_xyz", "priority": "P3"},
            headers=auth_headers,
        )

    resp = await client.get(f"{BASE}?q=unique_search_keyword_xyz", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["results"]["incidents"]) >= 1
