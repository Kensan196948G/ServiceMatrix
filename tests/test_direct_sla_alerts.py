"""sla.py エンドポイント直接呼び出しテスト - カバレッジ向上

対象: src/api/v1/sla.py
カバー対象行: 80-114 (get_sla_alerts の全分岐)
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_incident(
    incident_id=None,
    title="テストインシデント",
    priority="P1",
    status="In_Progress",
    sla_resolution_due_at=None,
    created_at=None,
    sla_breached=False,
):
    inc = MagicMock()
    inc.incident_id = incident_id or uuid.uuid4()
    inc.title = title
    inc.priority = priority
    inc.status = status
    inc.sla_resolution_due_at = sla_resolution_due_at
    inc.created_at = created_at or datetime.now(UTC) - timedelta(hours=10)
    inc.sla_breached = sla_breached
    return inc


def _make_db(incidents):
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = incidents
    db.execute = AsyncMock(return_value=result_mock)
    return db


# ─── get_sla_alerts (lines 80-114) ────────────────────────────────────────────


async def test_get_sla_alerts_with_alert_within_30_percent():
    """get_sla_alerts: 残時間30%以下 → アラート返却（line 105-113）"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)
    # total = 10 hours, remaining = 10 minutes → remaining_pct ≈ 1.7% → alert
    created_at = now - timedelta(hours=10)
    due = now + timedelta(minutes=10)

    inc = _make_incident(
        title="緊急インシデント",
        priority="P1",
        status="In_Progress",
        sla_resolution_due_at=due,
        created_at=created_at,
    )

    db = _make_db([inc])
    alerts = await get_sla_alerts(db=db)

    assert len(alerts) == 1
    assert alerts[0]["priority"] == "P1"
    assert alerts[0]["title"] == "緊急インシデント"
    assert alerts[0]["sla_remaining_percent"] < 30


async def test_get_sla_alerts_above_30_percent_excluded():
    """get_sla_alerts: 残時間30%超 → アラートなし"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)
    # total = 1 hour, remaining = 50 minutes → remaining_pct ≈ 83% → no alert
    created_at = now - timedelta(hours=1)
    due = now + timedelta(minutes=50)

    inc = _make_incident(
        title="余裕インシデント",
        priority="P3",
        status="In_Progress",
        sla_resolution_due_at=due,
        created_at=created_at,
    )

    db = _make_db([inc])
    alerts = await get_sla_alerts(db=db)

    assert len(alerts) == 0


async def test_get_sla_alerts_due_is_none_skipped():
    """get_sla_alerts: sla_resolution_due_at が None → continue でスキップ（line 94）"""
    from src.api.v1.sla import get_sla_alerts

    inc = _make_incident(
        title="期限なし",
        priority="P2",
        sla_resolution_due_at=None,
    )

    db = _make_db([inc])
    alerts = await get_sla_alerts(db=db)

    assert alerts == []


async def test_get_sla_alerts_total_zero_skipped():
    """get_sla_alerts: total <= 0 (due == created) → continue でスキップ（line 101）"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)
    # due == created → total = 0 → skip
    created_at = now
    due = now  # same time

    inc = _make_incident(
        title="ゼロ期間インシデント",
        sla_resolution_due_at=due,
        created_at=created_at,
    )

    db = _make_db([inc])
    alerts = await get_sla_alerts(db=db)

    assert alerts == []


async def test_get_sla_alerts_total_negative_skipped():
    """get_sla_alerts: due < created (total < 0) → continue でスキップ"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)
    created_at = now
    due = now - timedelta(hours=1)  # due BEFORE created → total < 0

    inc = _make_incident(
        title="逆転期間インシデント",
        sla_resolution_due_at=due,
        created_at=created_at,
    )

    db = _make_db([inc])
    alerts = await get_sla_alerts(db=db)

    assert alerts == []


async def test_get_sla_alerts_timezone_naive_due():
    """get_sla_alerts: timezone-naive な due を UTC として補完（lines 96-97）"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)
    # Timezone-naive datetime (lines 96-97 branch)
    created_at = datetime.now() - timedelta(hours=10)  # naive
    due = datetime.now() + timedelta(minutes=5)  # naive, within 30%

    inc = _make_incident(
        title="Naive-TZ インシデント",
        priority="P2",
        status="In_Progress",
        sla_resolution_due_at=due,
        created_at=created_at,
    )

    db = _make_db([inc])
    # Should not raise; timezone-naive datetimes are handled
    alerts = await get_sla_alerts(db=db)

    # Either alert or not depending on exact timing, but should not raise
    assert isinstance(alerts, list)


async def test_get_sla_alerts_timezone_naive_created():
    """get_sla_alerts: timezone-naive な created を UTC として補完（lines 98-99）"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)
    created_at = datetime(2026, 1, 1, 0, 0, 0)  # naive
    due = now + timedelta(minutes=5)  # aware, very close → alert

    inc = _make_incident(
        title="Naive-Created インシデント",
        priority="P1",
        status="In_Progress",
        sla_resolution_due_at=due,
        created_at=created_at,
    )

    db = _make_db([inc])
    alerts = await get_sla_alerts(db=db)

    # total is large (months), remaining is small → remaining_pct ≈ 0% → alert
    assert len(alerts) == 1


async def test_get_sla_alerts_multiple_incidents():
    """get_sla_alerts: 複数インシデント → フィルタ済みのみ返す"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)

    # Alert対象（残10分 / 10時間 ≈ 1.7%）
    inc_alert = _make_incident(
        title="アラート対象",
        priority="P1",
        sla_resolution_due_at=now + timedelta(minutes=10),
        created_at=now - timedelta(hours=10),
    )

    # 非対象（残2時間 / 3時間 ≈ 66%）
    inc_ok = _make_incident(
        title="余裕あり",
        priority="P3",
        sla_resolution_due_at=now + timedelta(hours=2),
        created_at=now - timedelta(hours=1),
    )

    db = _make_db([inc_alert, inc_ok])
    alerts = await get_sla_alerts(db=db)

    assert len(alerts) == 1
    assert alerts[0]["title"] == "アラート対象"


async def test_get_sla_alerts_empty_db():
    """get_sla_alerts: DBが空 → 空リスト"""
    from src.api.v1.sla import get_sla_alerts

    db = _make_db([])
    alerts = await get_sla_alerts(db=db)

    assert alerts == []


async def test_get_sla_alerts_result_fields():
    """get_sla_alerts: 返却オブジェクトが必要フィールドを含む（lines 107-112）"""
    from src.api.v1.sla import get_sla_alerts

    now = datetime.now(UTC)
    inc_id = uuid.uuid4()
    inc = _make_incident(
        incident_id=inc_id,
        title="フィールド確認",
        priority="P2",
        status="In_Progress",
        sla_resolution_due_at=now + timedelta(minutes=5),
        created_at=now - timedelta(hours=5),
    )

    db = _make_db([inc])
    alerts = await get_sla_alerts(db=db)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["incident_id"] == str(inc_id)
    assert alert["title"] == "フィールド確認"
    assert "sla_remaining_percent" in alert
    assert alert["priority"] == "P2"
