"""AI API エンドポイント統合テスト"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.services.ai_decision_log_service import AIDecision, AIDecisionLogService
from src.services.ai_triage_service import AITriageResult

pytestmark = pytest.mark.asyncio


# ─── フィクスチャ ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def incident_in_db(db_session):
    """類似検索テスト用インシデントをDBに作成"""
    from src.models.incident import Incident

    now = datetime.now(timezone.utc)
    inc = Incident(
        incident_id=uuid.uuid4(),
        incident_number="INC-TEST-000001",
        title="production database down outage",
        description="The primary database server is unreachable",
        priority="P1",
        status="New",
        created_at=now,
        updated_at=now,
    )
    db_session.add(inc)
    await db_session.flush()
    return inc


# ─── 類似インシデント検索 API ─────────────────────────────────────────────────

async def test_find_similar_incidents_returns_list(client, auth_headers, incident_in_db):
    """GET /ai/similar-incidents → 200, list返却"""
    resp = await client.get(
        "/api/v1/ai/similar-incidents",
        params={"title": "database down", "description": "db server unreachable"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_find_similar_incidents_match(client, auth_headers, incident_in_db):
    """類似インシデントが存在する場合、結果にincident_idが含まれる"""
    resp = await client.get(
        "/api/v1/ai/similar-incidents",
        params={"title": "production database outage"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    first = data[0]
    assert "incident_id" in first
    assert "incident_number" in first
    assert "title" in first
    assert "similarity" in first
    assert first["similarity"] > 0


async def test_find_similar_incidents_no_match(client, auth_headers, incident_in_db):
    """全く関係ないクエリ → 空リストまたは類似度ゼロ"""
    resp = await client.get(
        "/api/v1/ai/similar-incidents",
        params={"title": "zzz xyz qwerty"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_find_similar_incidents_limit(client, auth_headers, incident_in_db):
    """limit=1 → 最大1件返却"""
    resp = await client.get(
        "/api/v1/ai/similar-incidents",
        params={"title": "database down", "limit": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) <= 1


async def test_find_similar_incidents_no_auth(client):
    """認証なし → 401"""
    resp = await client.get(
        "/api/v1/ai/similar-incidents",
        params={"title": "test"},
    )
    assert resp.status_code == 401


async def test_find_similar_incidents_missing_title(client, auth_headers):
    """titleなし → 422"""
    resp = await client.get(
        "/api/v1/ai/similar-incidents",
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ─── AIトリアージAPI ──────────────────────────────────────────────────────────

async def test_triage_incident_success(client, auth_headers):
    """POST /ai/triage/{id} → モックで200"""
    mock_result = AITriageResult(
        priority="High",
        category="Database",
        confidence=0.8,
        reasoning="High keywords matched",
    )
    with patch(
        "src.api.v1.ai.ai_triage_service.apply_triage_to_incident",
        new=AsyncMock(return_value=mock_result),
    ):
        incident_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/ai/triage/{incident_id}",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == "High"
    assert data["category"] == "Database"
    assert data["confidence"] == 0.8


async def test_triage_incident_not_found(client, auth_headers):
    """存在しないインシデント → 404"""
    mock_result = AITriageResult(
        priority="Unknown",
        category="Unknown",
        confidence=0.0,
        reasoning="Incident not found",
    )
    with patch(
        "src.api.v1.ai.ai_triage_service.apply_triage_to_incident",
        new=AsyncMock(return_value=mock_result),
    ):
        resp = await client.post(
            f"/api/v1/ai/triage/{uuid.uuid4()}",
            headers=auth_headers,
        )
    assert resp.status_code == 404


async def test_triage_incident_no_auth(client):
    """認証なし → 401"""
    resp = await client.post(f"/api/v1/ai/triage/{uuid.uuid4()}")
    assert resp.status_code == 401


# ─── AI決定ログ ───────────────────────────────────────────────────────────────

async def test_decisions_list(client, auth_headers):
    """GET /ai/decisions → 200, list"""
    resp = await client.get("/api/v1/ai/decisions", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_decisions_list_filter_by_action(client, auth_headers):
    """action フィルタで絞り込み"""
    resp = await client.get(
        "/api/v1/ai/decisions",
        params={"action": "triage"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    for item in resp.json():
        assert item["action"] == "triage"


async def test_decisions_summary(client, auth_headers):
    """GET /ai/decisions/summary → 200, total/by_action/by_provider/avg_confidence"""
    resp = await client.get("/api/v1/ai/decisions/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_action" in data
    assert "by_provider" in data
    assert "avg_confidence" in data


async def test_decisions_no_auth(client):
    """認証なし → 401"""
    resp = await client.get("/api/v1/ai/decisions")
    assert resp.status_code == 401


# ─── AIDecisionLogService 単体テスト ──────────────────────────────────────────

async def test_decision_log_record_and_get():
    """recordしてget_decisionsで取得できる"""
    svc = AIDecisionLogService()
    now = datetime.now(timezone.utc)
    d = AIDecision(
        action="triage",
        entity_type="incident",
        entity_id="abc-123",
        input_data={"title": "test"},
        output_data={"priority": "High"},
        confidence=0.8,
        provider="keyword",
        timestamp=now,
    )
    await svc.record(d)
    results = await svc.get_decisions()
    assert len(results) == 1
    assert results[0].action == "triage"


async def test_decision_log_filter_by_entity_id():
    """entity_idフィルタ"""
    svc = AIDecisionLogService()
    now = datetime.now(timezone.utc)
    for eid in ["id-1", "id-2", "id-1"]:
        await svc.record(
            AIDecision(
                action="triage",
                entity_type="incident",
                entity_id=eid,
                input_data={},
                output_data={},
                confidence=0.5,
                provider="keyword",
                timestamp=now,
            )
        )
    results = await svc.get_decisions(entity_id="id-1")
    assert len(results) == 2


async def test_decision_log_get_summary():
    """get_summary の集計確認"""
    svc = AIDecisionLogService()
    now = datetime.now(timezone.utc)
    for action, conf in [("triage", 0.9), ("similar_search", 0.8), ("triage", 0.7)]:
        await svc.record(
            AIDecision(
                action=action,
                entity_type="incident",
                entity_id="x",
                input_data={},
                output_data={},
                confidence=conf,
                provider="keyword",
                timestamp=now,
            )
        )
    summary = await svc.get_summary()
    assert summary["total"] == 3
    assert summary["by_action"]["triage"] == 2
    assert summary["by_action"]["similar_search"] == 1
    assert abs(summary["avg_confidence"] - round((0.9 + 0.8 + 0.7) / 3, 4)) < 0.001
