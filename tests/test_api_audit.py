"""監査ログAPI 統合テスト"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


def _make_audit_log(db_session, seq: int, resource_type: str | None = None,
                    resource_id: str | None = None):
    """テスト用 AuditLog を直接生成（シーケンサー不使用）"""
    from src.models.audit import AuditLog

    now = datetime.now(timezone.utc)
    prev_hash = None
    log_data = {
        "sequence_number": seq,
        "created_at": now.isoformat(),
        "user_id": None,
        "action": "test_action",
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    import hashlib, json  # noqa: E401
    chain_input = (prev_hash or "") + json.dumps(log_data, sort_keys=True, default=str)
    current_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()

    log = AuditLog(
        log_id=uuid.uuid4(),
        created_at=now,
        action="test_action",
        resource_type=resource_type,
        resource_id=resource_id,
        prev_log_hash=prev_hash,
        current_hash=current_hash,
        sequence_number=seq,
    )
    db_session.add(log)
    return log


# ─── テスト ──────────────────────────────────────────────────────────────────

async def test_list_audit_logs_empty(client, auth_headers):
    """GET /api/v1/audit/logs - 空のリスト"""
    resp = await client.get("/api/v1/audit/logs", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_audit_logs_with_data(client, auth_headers, db_session):
    """監査ログあり → 一覧返却"""
    _make_audit_log(db_session, seq=1001)
    _make_audit_log(db_session, seq=1002)
    await db_session.flush()

    resp = await client.get("/api/v1/audit/logs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    # sequence_number 降順
    seqs = [d["sequence_number"] for d in data]
    assert seqs == sorted(seqs, reverse=True)


async def test_filter_audit_logs_by_entity_type(client, auth_headers, db_session):
    """entity_typeフィルタ"""
    _make_audit_log(db_session, seq=2001, resource_type="incident")
    _make_audit_log(db_session, seq=2002, resource_type="problem")
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/logs", params={"entity_type": "incident"}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(d["entity_type"] == "incident" for d in data)


async def test_filter_audit_logs_by_entity_id(client, auth_headers, db_session):
    """entity_idフィルタ"""
    target_id = "INC-2024-000001"
    _make_audit_log(db_session, seq=3001, resource_type="incident", resource_id=target_id)
    _make_audit_log(db_session, seq=3002, resource_type="incident", resource_id="INC-2024-000002")
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/logs", params={"entity_id": target_id}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(d["entity_id"] == target_id for d in data)


async def test_get_entity_audit_logs(client, auth_headers, db_session):
    """GET /api/v1/audit/logs/{entity_type}/{entity_id}"""
    _make_audit_log(db_session, seq=4001, resource_type="change", resource_id="CHG-001")
    await db_session.flush()

    resp = await client.get("/api/v1/audit/logs/change/CHG-001", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["entity_type"] == "change"
    assert data[0]["entity_id"] == "CHG-001"


async def test_verify_chain_empty(client, auth_headers):
    """POST /api/v1/audit/verify-chain - ログなし → is_valid=True"""
    resp = await client.post(
        "/api/v1/audit/verify-chain",
        params={"start_seq": 99999, "end_seq": 99999},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["first_invalid_sequence"] is None


async def test_verify_chain_valid(client, auth_headers, db_session):
    """整合性OK → is_valid=True"""
    from sqlalchemy import select

    from src.models.audit import AuditLog
    from src.services.audit_service import compute_hash

    seq_base = 50000
    now = datetime.now(timezone.utc)
    for i in range(3):
        log = AuditLog(
            log_id=uuid.uuid4(),
            created_at=now,
            action="test_action",
            prev_log_hash=None,
            current_hash="placeholder",
            sequence_number=seq_base + i,
        )
        db_session.add(log)
    await db_session.flush()

    # Re-fetch to get DB-round-tripped datetimes, then set correct chain hashes
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.sequence_number.between(seq_base, seq_base + 2))
        .order_by(AuditLog.sequence_number)
    )
    fetched = result.scalars().all()
    prev_hash = None
    for log in fetched:
        log_data = {
            "sequence_number": log.sequence_number,
            "created_at": log.created_at.isoformat(),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
        }
        current_hash = compute_hash(prev_hash, log_data)
        log.prev_log_hash = prev_hash
        log.current_hash = current_hash
        prev_hash = current_hash
    await db_session.flush()

    resp = await client.post(
        "/api/v1/audit/verify-chain",
        params={"start_seq": seq_base, "end_seq": seq_base + 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["checked_count"] == 3


async def test_audit_logs_pagination(client, auth_headers, db_session):
    """limit/offsetページネーション"""
    for i in range(10):
        _make_audit_log(db_session, seq=60000 + i)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/logs",
        params={"entity_type": None, "limit": 3, "offset": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 3

    resp2 = await client.get(
        "/api/v1/audit/logs",
        params={"limit": 3, "offset": 3},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    seqs1 = {d["sequence_number"] for d in data}
    seqs2 = {d["sequence_number"] for d in data2}
    assert seqs1.isdisjoint(seqs2)


# ─── 統計 ────────────────────────────────────────────────────────────────────

async def test_get_audit_stats_empty(client, auth_headers):
    """GET /api/v1/audit/stats - データなし → total_operations=0"""
    resp = await client.get("/api/v1/audit/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_operations" in data
    assert "unique_users" in data
    assert "by_action" in data
    assert "by_resource" in data
    assert "recent_activity" in data
    assert isinstance(data["total_operations"], int)
    assert isinstance(data["unique_users"], int)


async def test_get_audit_stats_with_data(client, auth_headers, db_session):
    """GET /api/v1/audit/stats - データあり → 集計結果返却"""
    _make_audit_log(db_session, seq=70001, resource_type="incident")
    _make_audit_log(db_session, seq=70002, resource_type="change")
    _make_audit_log(db_session, seq=70003, resource_type="incident")
    await db_session.flush()

    resp = await client.get("/api/v1/audit/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_operations"] >= 3
    assert isinstance(data["by_action"], dict)
    assert isinstance(data["by_resource"], dict)
    assert isinstance(data["recent_activity"], list)


async def test_get_audit_stats_unauthorized(client):
    """GET /api/v1/audit/stats - 認証なし → 401"""
    resp = await client.get("/api/v1/audit/stats")
    assert resp.status_code == 401


# ─── CSV エクスポート ─────────────────────────────────────────────────────────

async def test_export_audit_logs_csv(client, auth_headers, db_session):
    """GET /api/v1/audit/logs/export - CSV形式でダウンロード"""
    _make_audit_log(db_session, seq=80001, resource_type="incident", resource_id="INC-001")
    _make_audit_log(db_session, seq=80002, resource_type="change", resource_id="CHG-001")
    await db_session.flush()

    resp = await client.get("/api/v1/audit/logs/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    content = resp.text
    # CSVヘッダー行が含まれること
    assert "timestamp" in content
    assert "action" in content


async def test_export_audit_logs_filter_by_entity_type(client, auth_headers, db_session):
    """GET /api/v1/audit/logs/export?entity_type=incident - フィルタ付きエクスポート"""
    _make_audit_log(db_session, seq=81001, resource_type="incident")
    _make_audit_log(db_session, seq=81002, resource_type="problem")
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/logs/export",
        params={"entity_type": "incident"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    content = resp.text
    assert "incident" in content


async def test_export_audit_logs_unauthorized(client):
    """GET /api/v1/audit/logs/export - 認証なし → 401"""
    resp = await client.get("/api/v1/audit/logs/export")
    assert resp.status_code == 401


async def test_verify_chain_invalid(client, auth_headers, db_session):
    """ハッシュが不正なログ → is_valid=False"""
    from src.models.audit import AuditLog

    now = datetime.now(timezone.utc)
    bad_log = AuditLog(
        log_id=uuid.uuid4(),
        created_at=now,
        action="tampered_action",
        prev_log_hash=None,
        current_hash="000000000000000000000000000000000000000000000000000000000000INVALID",
        sequence_number=90001,
    )
    db_session.add(bad_log)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/audit/verify-chain",
        params={"start_seq": 90001, "end_seq": 90001},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # 不正ハッシュ → is_valid=False
    assert data["is_valid"] is False
    assert data["first_invalid_sequence"] == 90001


async def test_list_audit_logs_unauthorized(client):
    """GET /api/v1/audit/logs - 認証なし → 401"""
    resp = await client.get("/api/v1/audit/logs")
    assert resp.status_code == 401


async def test_verify_chain_unauthorized(client):
    """POST /api/v1/audit/verify-chain - 認証なし → 401"""
    resp = await client.post(
        "/api/v1/audit/verify-chain",
        params={"start_seq": 1, "end_seq": 10},
    )
    assert resp.status_code == 401
