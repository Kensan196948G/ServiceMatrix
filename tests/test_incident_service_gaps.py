"""incident_service.py サービス層直接テスト - カバレッジ向上

対象: src/services/incident_service.py
カバー対象行: 40-43, 69-84, 105, 111-112, 118-119, 125-135
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_db_for_nextval(seq_value: int = 1):
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = seq_value
    db.execute = AsyncMock(return_value=result_mock)
    return db


def _make_incident_mock(
    incident_id=None,
    status="New",
    priority="P1",
    acknowledged_at=None,
    sla_response_due_at=None,
    sla_resolution_due_at=None,
    sla_breached=False,
):
    inc = MagicMock()
    inc.incident_id = incident_id or uuid.uuid4()
    inc.incident_number = "INC-2026-000001"
    inc.status = status
    inc.priority = priority
    inc.acknowledged_at = acknowledged_at
    inc.sla_response_due_at = sla_response_due_at
    inc.sla_resolution_due_at = sla_resolution_due_at
    inc.sla_breached = sla_breached
    inc.resolved_at = None
    inc.closed_at = None
    return inc


# ─── _get_next_incident_number (lines 40-43) ──────────────────────────────────


async def test_get_next_incident_number_format():
    """_get_next_incident_number: INC-YYYY-NNNNNN 形式で返す（lines 40-43）"""
    from src.services.incident_service import _get_next_incident_number

    db = _make_db_for_nextval(seq_value=42)
    result = await _get_next_incident_number(db)

    year = datetime.now(UTC).year
    assert result == f"INC-{year}-000042"


async def test_get_next_incident_number_padding():
    """_get_next_incident_number: シーケンス番号は6桁ゼロ埋め"""
    from src.services.incident_service import _get_next_incident_number

    db = _make_db_for_nextval(seq_value=1)
    result = await _get_next_incident_number(db)

    assert result.endswith("-000001")


async def test_get_next_incident_number_large_sequence():
    """_get_next_incident_number: 大きなシーケンス番号も正しくフォーマット"""
    from src.services.incident_service import _get_next_incident_number

    db = _make_db_for_nextval(seq_value=123456)
    result = await _get_next_incident_number(db)

    assert result.endswith("-123456")


# ─── create_incident (lines 69-84) ─────────────────────────────────────────────


async def test_create_incident_broadcasts_notification():
    """create_incident: WebSocket通知を broadcast する（lines 69-84）"""
    from src.services.incident_service import create_incident

    db = _make_db_for_nextval(seq_value=1)
    db.add = MagicMock()

    inc_instance = _make_incident_mock(
        status="New",
        priority="P1",
    )
    inc_instance.incident_number = "INC-2026-000001"

    with patch("src.services.incident_service.Incident", return_value=inc_instance):
        with patch("src.services.notification_manager.manager") as mock_mgr:
            mock_mgr.broadcast_incident_update = AsyncMock()
            result = await create_incident(db, {"title": "テスト", "priority": "P1"})

    mock_mgr.broadcast_incident_update.assert_called_once()
    call_args = mock_mgr.broadcast_incident_update.call_args
    assert call_args[0][1] == "created"


async def test_create_incident_returns_incident_object():
    """create_incident: Incident オブジェクトを返す"""
    from src.services.incident_service import create_incident

    db = _make_db_for_nextval(seq_value=5)
    db.add = MagicMock()

    inc_instance = _make_incident_mock(priority="P2")
    inc_instance.incident_number = "INC-2026-000005"

    with patch("src.services.incident_service.Incident", return_value=inc_instance):
        with patch("src.services.notification_manager.manager") as mock_mgr:
            mock_mgr.broadcast_incident_update = AsyncMock()
            result = await create_incident(db, {"title": "P2テスト", "priority": "P2"})

    assert result is inc_instance
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(inc_instance)


async def test_create_incident_increments_metrics():
    """create_incident: metrics.incidents_created_total をインクリメント"""
    from src.services.incident_service import create_incident
    from src.core.metrics import metrics

    db = _make_db_for_nextval(seq_value=10)
    db.add = MagicMock()

    inc_instance = _make_incident_mock()
    inc_instance.incident_number = "INC-2026-000010"

    before = metrics.incidents_created_total

    with patch("src.services.incident_service.Incident", return_value=inc_instance):
        with patch("src.services.notification_manager.manager") as mock_mgr:
            mock_mgr.broadcast_incident_update = AsyncMock()
            await create_incident(db, {"title": "メトリクスtest", "priority": "P3"})

    assert metrics.incidents_created_total == before + 1


# ─── transition_status (lines 105, 111-112, 118-119, 125-135) ────────────────


async def test_transition_status_acknowledge_with_sla_breach():
    """transition_status: Acknowledged でSLA応答期限超過 → sla_breached=True（lines 111-112）"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    # sla_response_due_at が過去 → SLA超過
    past_due = datetime.now(UTC) - timedelta(hours=1)
    inc = _make_incident_mock(
        status="New",
        acknowledged_at=None,
        sla_response_due_at=past_due,
    )

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        result = await transition_status(db, inc, "Acknowledged")

    assert inc.sla_breached is True
    assert inc.acknowledged_at is not None


async def test_transition_status_acknowledge_timezone_naive_sla_due():
    """transition_status: timezone-naive な sla_response_due_at → UTC補完（line 105）"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    # Timezone-naive datetime → _aware が UTC として補完（line 104-105）
    naive_past_due = datetime(2020, 1, 1, 12, 0, 0)  # no tzinfo, far past
    inc = _make_incident_mock(
        status="New",
        acknowledged_at=None,
        sla_response_due_at=naive_past_due,
    )

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        await transition_status(db, inc, "Acknowledged")

    # naive datetime が UTC として扱われ、SLA違反が検出される
    assert inc.sla_breached is True


async def test_transition_status_acknowledge_no_breach_when_within_sla():
    """transition_status: Acknowledged でSLA応答期限内 → sla_breached=False"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    future_due = datetime.now(UTC) + timedelta(hours=1)
    inc = _make_incident_mock(
        status="New",
        acknowledged_at=None,
        sla_response_due_at=future_due,
    )

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        await transition_status(db, inc, "Acknowledged")

    assert inc.sla_breached is False


async def test_transition_status_resolve_with_sla_breach():
    """transition_status: Resolved でSLA解決期限超過 → sla_breached=True（lines 118-119）"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    past_due = datetime.now(UTC) - timedelta(hours=2)
    inc = _make_incident_mock(
        status="In_Progress",
        sla_resolution_due_at=past_due,
    )

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        result = await transition_status(db, inc, "Resolved")

    assert inc.sla_breached is True
    assert inc.resolved_at is not None


async def test_transition_status_resolve_no_breach_when_within_sla():
    """transition_status: Resolved でSLA解決期限内 → sla_breached=False"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    future_due = datetime.now(UTC) + timedelta(hours=3)
    inc = _make_incident_mock(
        status="In_Progress",
        sla_resolution_due_at=future_due,
    )

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        await transition_status(db, inc, "Resolved")

    assert inc.sla_breached is False


async def test_transition_status_close_sets_closed_at():
    """transition_status: Closed → closed_at が設定される（line 121-122）"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    inc = _make_incident_mock(status="Resolved")

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        await transition_status(db, inc, "Closed")

    assert inc.closed_at is not None


async def test_transition_status_broadcasts_updated():
    """transition_status: flush/refresh + broadcast 'updated'（lines 125-135）"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    inc = _make_incident_mock(status="New")

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        await transition_status(db, inc, "Acknowledged")

    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(inc)
    mock_mgr.broadcast_incident_update.assert_called_once()
    call_args = mock_mgr.broadcast_incident_update.call_args
    assert call_args[0][1] == "updated"


async def test_transition_status_broadcasts_closed():
    """transition_status: Closed 遷移 → action='closed'（line 129）"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    inc = _make_incident_mock(status="Resolved")

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        await transition_status(db, inc, "Closed")

    call_args = mock_mgr.broadcast_incident_update.call_args
    assert call_args[0][1] == "closed"


async def test_transition_status_invalid_transition_raises():
    """transition_status: 無効遷移 → ValueError"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    inc = _make_incident_mock(status="New")

    with pytest.raises(ValueError, match="遷移は許可されていません"):
        await transition_status(db, inc, "Closed")


async def test_transition_status_acknowledge_already_acked():
    """transition_status: acknowledged_at 既設定 → 再設定なし（line 107 条件False）"""
    from src.services.incident_service import transition_status

    db = AsyncMock()
    already_acked = datetime.now(UTC) - timedelta(minutes=5)
    inc = _make_incident_mock(
        status="New",
        acknowledged_at=already_acked,  # 既にAcknowledge済み
        sla_response_due_at=datetime.now(UTC) - timedelta(hours=1),
    )

    with patch("src.services.notification_manager.manager") as mock_mgr:
        mock_mgr.broadcast_incident_update = AsyncMock()
        await transition_status(db, inc, "Acknowledged")

    # acknowledged_at は変更されない
    assert inc.acknowledged_at == already_acked
    # sla_breached も変更されない（if ブロックに入らないため）
    assert inc.sla_breached is False
