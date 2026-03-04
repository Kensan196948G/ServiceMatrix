"""コンプライアンス API エンドポイント統合テスト"""
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
        username=f"comp_admin_{uid.hex[:8]}",
        email=f"comp_{uid.hex[:8]}@test.com",
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

BASE = "/api/v1/compliance"


# ─── SOC2 チェックリスト ─────────────────────────────────────────────────────

async def test_get_soc2_checks(client, auth_headers):
    """GET /compliance/checks/soc2 → 200, checks/summary 構造"""
    resp = await client.get(f"{BASE}/checks/soc2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "checks" in data
    assert "summary" in data
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0


async def test_soc2_checks_have_required_fields(client, auth_headers):
    """SOC2 チェック項目に必須フィールドが含まれる"""
    resp = await client.get(f"{BASE}/checks/soc2", headers=auth_headers)
    assert resp.status_code == 200
    checks = resp.json()["checks"]
    for check in checks:
        assert "id" in check
        assert "category" in check
        assert "title" in check
        assert "status" in check
        assert check["status"] in ("PASS", "FAIL", "MANUAL")


async def test_soc2_summary_fields(client, auth_headers):
    """SOC2 サマリーに total/pass/fail/manual/score が含まれる"""
    resp = await client.get(f"{BASE}/checks/soc2", headers=auth_headers)
    summary = resp.json()["summary"]
    assert "total" in summary
    assert "pass" in summary
    assert "fail" in summary
    assert "manual" in summary
    assert "score" in summary
    assert 0 <= summary["score"] <= 100


# ─── ISO27001 チェックリスト ─────────────────────────────────────────────────

async def test_get_iso27001_checks(client, auth_headers):
    """GET /compliance/checks/iso27001 → 200, checks/summary 構造"""
    resp = await client.get(f"{BASE}/checks/iso27001", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "checks" in data
    assert "summary" in data
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0


async def test_iso27001_checks_have_required_fields(client, auth_headers):
    """ISO27001 チェック項目に必須フィールドが含まれる"""
    resp = await client.get(f"{BASE}/checks/iso27001", headers=auth_headers)
    checks = resp.json()["checks"]
    for check in checks:
        assert "id" in check
        assert check["status"] in ("PASS", "FAIL", "MANUAL")


# ─── 統合レポート ────────────────────────────────────────────────────────────

async def test_get_compliance_report(client, auth_headers):
    """GET /compliance/report → 200, soc2/iso27001/overall 構造"""
    resp = await client.get(f"{BASE}/report", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "soc2" in data
    assert "iso27001" in data
    assert "overall" in data
    assert "summary" in data["soc2"]
    assert "summary" in data["iso27001"]
    assert "summary" in data["overall"]


# ─── スコア ──────────────────────────────────────────────────────────────────

async def test_get_compliance_score(client, auth_headers):
    """GET /compliance/score → 200, overall_score/soc2_score/iso27001_score"""
    resp = await client.get(f"{BASE}/score", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "soc2_score" in data
    assert "iso27001_score" in data
    assert 0 <= data["overall_score"] <= 100


# ─── 認証 ────────────────────────────────────────────────────────────────────

async def test_soc2_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(f"{BASE}/checks/soc2")
    assert resp.status_code == 401


async def test_iso27001_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(f"{BASE}/checks/iso27001")
    assert resp.status_code == 401


async def test_report_unauthorized(client):
    """認証なし → 401"""
    resp = await client.get(f"{BASE}/report")
    assert resp.status_code == 401
