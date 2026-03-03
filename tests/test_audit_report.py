"""監査ログ J-SOXコンプライアンスレポートAPI テスト"""

import hashlib
import json
import uuid
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.asyncio


def _make_audit_log(
    db_session,
    seq: int,
    action: str = "test_action",
    resource_type: str | None = None,
    resource_id: str | None = None,
    user_id: uuid.UUID | None = None,
    username: str | None = None,
    user_role: str | None = None,
    prev_hash: str | None = None,
):
    """テスト用 AuditLog を直接生成（シーケンサー不使用）"""
    from src.models.audit import AuditLog

    now = datetime.now(UTC)
    log_data = {
        "sequence_number": seq,
        "created_at": now.isoformat(),
        "user_id": str(user_id) if user_id else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    chain_input = (prev_hash or "") + json.dumps(log_data, sort_keys=True, default=str)
    current_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()

    log = AuditLog(
        log_id=uuid.uuid4(),
        created_at=now,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        username=username,
        user_role=user_role,
        prev_log_hash=prev_hash,
        current_hash=current_hash,
        sequence_number=seq,
    )
    db_session.add(log)
    return log


# ─── 1. コンプライアンスレポート エンドポイント ──────────────────────────────


async def test_compliance_report_empty(client, auth_headers):
    """GET /api/v1/audit/report/compliance - データなし"""
    resp = await client.get("/api/v1/audit/report/compliance", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_logs" in data
    assert "hash_chain_valid" in data
    assert "actions_by_type" in data
    assert "top_users" in data
    assert "security_events" in data
    assert data["total_logs"] == 0
    assert data["hash_chain_valid"] is True


async def test_compliance_report_with_logs(client, auth_headers, db_session):
    """コンプライアンスレポート - ログあり"""
    _make_audit_log(db_session, seq=70001, action="CI_CREATE", resource_type="ConfigurationItem")
    _make_audit_log(db_session, seq=70002, action="CI_UPDATE", resource_type="ConfigurationItem")
    _make_audit_log(db_session, seq=70003, action="INCIDENT_CREATE", resource_type="Incident")
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/report/compliance",
        params={"days": 30},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_logs"] >= 3
    assert isinstance(data["actions_by_type"], list)
    assert len(data["actions_by_type"]) >= 1


async def test_compliance_report_days_param(client, auth_headers):
    """コンプライアンスレポート - days/start_seq/end_seqパラメータ"""
    resp = await client.get(
        "/api/v1/audit/report/compliance",
        params={"days": 7, "start_seq": 1, "end_seq": 100},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "period_start" in data
    assert "period_end" in data


# ─── 2. セキュリティイベントサマリー エンドポイント ─────────────────────────


async def test_security_events_empty(client, auth_headers):
    """GET /api/v1/audit/report/security-events - セキュリティイベントなし"""
    resp = await client.get("/api/v1/audit/report/security-events", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "auth_failures" in data
    assert "privilege_escalations" in data
    assert "total_events" in data
    assert "top_actions" in data
    assert isinstance(data["top_actions"], list)


async def test_security_events_with_failures(client, auth_headers, db_session):
    """セキュリティイベントあり - LOGIN_FAILED検知"""
    _make_audit_log(db_session, seq=71001, action="LOGIN_FAILED")
    _make_audit_log(db_session, seq=71002, action="LOGIN_FAILED")
    _make_audit_log(db_session, seq=71003, action="UNAUTHORIZED_ACCESS")
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/report/security-events",
        params={"days": 30},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_failures"] >= 2
    assert data["total_events"] >= 2


async def test_security_events_privilege_escalation(client, auth_headers, db_session):
    """権限昇格イベント検知"""
    _make_audit_log(db_session, seq=71101, action="PRIVILEGE_ESCALATION")
    _make_audit_log(db_session, seq=71102, action="ROLE_CHANGE")
    await db_session.flush()

    resp = await client.get("/api/v1/audit/report/security-events", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["privilege_escalations"] >= 2


# ─── 3. ユーザーアクティビティレポート エンドポイント ───────────────────────


async def test_user_activity_empty(client, auth_headers):
    """GET /api/v1/audit/report/user-activity - ユーザーなし"""
    resp = await client.get("/api/v1/audit/report/user-activity", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "items" in data
    assert isinstance(data["items"], list)


async def test_user_activity_with_users(client, auth_headers, db_session):
    """ユーザーアクティビティ - ユーザーあり"""
    user_id_1 = uuid.uuid4()
    user_id_2 = uuid.uuid4()
    _make_audit_log(
        db_session,
        seq=72001,
        action="LOGIN",
        user_id=user_id_1,
        username="alice",
        user_role="Operator",
    )
    _make_audit_log(
        db_session,
        seq=72002,
        action="CI_CREATE",
        user_id=user_id_1,
        username="alice",
        user_role="Operator",
    )
    _make_audit_log(
        db_session, seq=72003, action="LOGIN", user_id=user_id_2, username="bob", user_role="Viewer"
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/report/user-activity",
        params={"days": 30, "limit": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_users"] >= 2
    assert len(data["items"]) >= 2
    # アクション数降順に並ぶ
    counts = [item["action_count"] for item in data["items"]]
    assert counts == sorted(counts, reverse=True)


async def test_user_activity_limit_param(client, auth_headers):
    """limit パラメータ有効"""
    resp = await client.get(
        "/api/v1/audit/report/user-activity",
        params={"limit": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 5


# ─── 4. 監査ログエクスポート エンドポイント ─────────────────────────────────


async def test_export_empty(client, auth_headers):
    """GET /api/v1/audit/export - データなし"""
    resp = await client.get(
        "/api/v1/audit/export",
        params={"entity_type": "NonExistentType9999"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "exported_at" in data
    assert "total_records" in data
    assert "filters_applied" in data
    assert "records" in data
    assert data["total_records"] == 0
    assert isinstance(data["records"], list)


async def test_export_with_data(client, auth_headers, db_session):
    """エクスポート - データあり"""
    _make_audit_log(db_session, seq=73001, action="CI_CREATE", resource_type="ExportTest")
    _make_audit_log(db_session, seq=73002, action="CI_UPDATE", resource_type="ExportTest")
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/export",
        params={"entity_type": "ExportTest"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_records"] >= 2
    assert data["filters_applied"].get("entity_type") == "ExportTest"
    assert len(data["records"]) >= 2


async def test_export_filter_by_entity_id(client, auth_headers, db_session):
    """エクスポート - entity_idフィルタ"""
    _make_audit_log(
        db_session, seq=73101, action="CI_CREATE", resource_type="CI", resource_id="ci-export-001"
    )
    _make_audit_log(
        db_session, seq=73102, action="CI_UPDATE", resource_type="CI", resource_id="ci-export-999"
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/export",
        params={"entity_id": "ci-export-001"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_records"] >= 1
    assert all(r["entity_id"] == "ci-export-001" for r in data["records"])


async def test_export_limit_applied(client, auth_headers, db_session):
    """エクスポート - limit適用"""
    for i in range(5):
        _make_audit_log(db_session, seq=73200 + i, action="BULK_EXPORT_TEST")
    await db_session.flush()

    resp = await client.get(
        "/api/v1/audit/export",
        params={"limit": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["records"]) <= 2


# ─── 5. サービス関数 直接呼び出しテスト（カバレッジ向上） ────────────────────


async def test_generate_compliance_report_direct(db_session):
    """generate_compliance_report 直接呼び出し"""
    from src.services.audit_service import generate_compliance_report

    _make_audit_log(db_session, seq=80001, action="DIRECT_TEST")
    await db_session.flush()

    report = await generate_compliance_report(db_session, days=30, start_seq=80001, end_seq=80001)
    assert report.total_logs >= 1
    assert isinstance(report.hash_chain_valid, bool)
    assert isinstance(report.actions_by_type, list)
    assert isinstance(report.top_users, list)


async def test_get_security_events_direct(db_session):
    """get_security_events_summary 直接呼び出し"""
    from src.services.audit_service import get_security_events_summary

    summary = await get_security_events_summary(db_session, days=30)
    assert summary.auth_failures >= 0
    assert summary.privilege_escalations >= 0
    assert isinstance(summary.top_actions, list)


async def test_get_user_activity_direct(db_session):
    """get_user_activity_summary 直接呼び出し"""
    from src.services.audit_service import get_user_activity_summary

    uid = uuid.uuid4()
    _make_audit_log(
        db_session,
        seq=81001,
        action="DIRECT_USER_TEST",
        user_id=uid,
        username="direct_user",
        user_role="Operator",
    )
    await db_session.flush()

    result = await get_user_activity_summary(db_session, days=30, limit=10)
    assert result.total_users >= 1
    assert isinstance(result.items, list)


async def test_export_audit_logs_direct(db_session):
    """export_audit_logs 直接呼び出し"""
    from src.services.audit_service import export_audit_logs

    _make_audit_log(
        db_session, seq=82001, action="EXPORT_DIRECT_TEST", resource_type="DirectExportType"
    )
    await db_session.flush()

    logs, filters = await export_audit_logs(db_session, entity_type="DirectExportType", limit=100)
    assert len(logs) >= 1
    assert filters["entity_type"] == "DirectExportType"
