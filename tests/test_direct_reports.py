"""レポートAPI 直接呼び出しカバレッジテスト

対象: src/api/v1/reports.py
目的: 実データ（MTTR計算・SLA違反・バケット分岐）のパスをカバー
カバー対象行: 44-70, 77-84, 88, 132-156, 168-171
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────


def _make_user():
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = UserRole.SYSTEM_ADMIN
    return u


def _make_incident(
    *,
    resolved_hours: float | None = None,
    sla_breached: bool = False,
    status: str = "Resolved",
    affected_service: str | None = "Web",
):
    """インシデントモックを生成"""
    inc = MagicMock()
    inc.status = status
    inc.sla_breached = sla_breached
    inc.affected_service = affected_service

    base = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    inc.created_at = base

    if resolved_hours is not None:
        inc.resolved_at = base + timedelta(hours=resolved_hours)
    else:
        inc.resolved_at = None

    return inc


def _make_change(*, status: str = "Completed"):
    chg = MagicMock()
    chg.status = status
    chg.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    return chg


def _make_db_with_incidents(incidents, changes=None):
    """インシデント/変更を返すDBセッションモック"""
    if changes is None:
        changes = []
    db = MagicMock()

    inc_scalars = MagicMock()
    inc_scalars.all.return_value = incidents
    inc_result = MagicMock()
    inc_result.scalars.return_value = inc_scalars

    chg_scalars = MagicMock()
    chg_scalars.all.return_value = changes
    chg_result = MagicMock()
    chg_result.scalars.return_value = chg_scalars

    # 1回目の execute がインシデント、2回目が変更
    db.execute = AsyncMock(side_effect=[inc_result, chg_result])
    return db


def _make_db_for_distribution(incidents):
    """解決時間分布用DBモック（1回のexecuteのみ）"""
    db = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = incidents
    result = MagicMock()
    result.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result)
    return db


# ─── get_stats テスト ───────────────────────────────────────


async def test_get_stats_with_resolved_incidents():
    """解決済みインシデントのMTTR計算をカバー"""
    from src.api.v1.reports import get_stats

    incidents = [
        _make_incident(resolved_hours=2.0, sla_breached=False, affected_service="Web"),
        _make_incident(resolved_hours=6.0, sla_breached=False, affected_service="DB"),
        _make_incident(resolved_hours=None, sla_breached=False, status="Open", affected_service="API"),
    ]
    changes = [
        _make_change(status="Completed"),
        _make_change(status="Failed"),
    ]
    db = _make_db_with_incidents(incidents, changes)
    user = _make_user()

    result = await get_stats(db=db, current_user=user, year=2026, month=1)

    assert result["incidents"]["total"] == 3
    assert result["incidents"]["resolved"] == 2
    # MTTR = (2.0 + 6.0) / 2 = 4.0
    assert result["mttr_hours"] == 4.0
    assert result["changes"]["total"] == 2
    assert result["changes"]["completed"] == 1
    assert result["changes"]["failed"] == 1


async def test_get_stats_with_sla_breached():
    """SLA違反ありのsla_compliance_rate計算をカバー"""
    from src.api.v1.reports import get_stats

    incidents = [
        _make_incident(resolved_hours=1.0, sla_breached=True, affected_service="Web"),
        _make_incident(resolved_hours=2.0, sla_breached=False, affected_service="Web"),
        _make_incident(resolved_hours=3.0, sla_breached=False, affected_service="Web"),
        _make_incident(resolved_hours=4.0, sla_breached=False, affected_service="API"),
    ]
    db = _make_db_with_incidents(incidents)
    user = _make_user()

    result = await get_stats(db=db, current_user=user, year=2026, month=1)

    # sla_compliance = 1 - 1/4 = 0.75
    assert result["sla_compliance_rate"] == 0.75
    assert result["mtbf_hours"] > 0


async def test_get_stats_all_breached():
    """全インシデントSLA違反（rate=0）"""
    from src.api.v1.reports import get_stats

    incidents = [
        _make_incident(resolved_hours=10.0, sla_breached=True),
        _make_incident(resolved_hours=20.0, sla_breached=True),
    ]
    db = _make_db_with_incidents(incidents)
    user = _make_user()

    result = await get_stats(db=db, current_user=user, year=2026, month=1)

    assert result["sla_compliance_rate"] == 0.0


async def test_get_stats_zero_incidents():
    """インシデントなし（MTBF=期間全時間、SLA=1.0）"""
    from src.api.v1.reports import get_stats

    db = _make_db_with_incidents([])
    user = _make_user()

    result = await get_stats(db=db, current_user=user, year=2026, month=1)

    assert result["incidents"]["total"] == 0
    assert result["mttr_hours"] == 0.0
    assert result["sla_compliance_rate"] == 1.0
    # MTBF = 31 * 24 = 744h
    assert result["mtbf_hours"] == 744.0


async def test_get_stats_top_services_aggregation():
    """影響サービス上位5件の集計ロジックをカバー"""
    from src.api.v1.reports import get_stats

    incidents = []
    for _ in range(5):
        incidents.append(_make_incident(affected_service="Web"))
    for _ in range(3):
        incidents.append(_make_incident(affected_service="DB"))
    for _ in range(2):
        incidents.append(_make_incident(affected_service="API"))

    db = _make_db_with_incidents(incidents)
    user = _make_user()

    result = await get_stats(db=db, current_user=user, year=2026, month=1)

    top = result["top_affected_services"]
    assert len(top) <= 5
    assert top[0]["service"] == "Web"
    assert top[0]["count"] == 5


async def test_get_stats_unknown_service():
    """affected_service が None の場合 '不明' として集計"""
    from src.api.v1.reports import get_stats

    incidents = [
        _make_incident(affected_service=None),
        _make_incident(affected_service=None),
    ]
    db = _make_db_with_incidents(incidents)
    user = _make_user()

    result = await get_stats(db=db, current_user=user, year=2026, month=1)

    top = result["top_affected_services"]
    services = [t["service"] for t in top]
    assert "不明" in services


async def test_get_stats_no_resolved_at():
    """resolved_at が None のインシデントがあっても MTTR 計算でクラッシュしない"""
    from src.api.v1.reports import get_stats

    incidents = [
        _make_incident(resolved_hours=None, sla_breached=False, status="Open"),
    ]
    db = _make_db_with_incidents(incidents)
    user = _make_user()

    result = await get_stats(db=db, current_user=user, year=2026, month=1)

    assert result["mttr_hours"] == 0.0


# ─── get_resolution_distribution テスト ────────────────────


async def test_resolution_distribution_all_buckets():
    """全5バケット（<1h, 1-4h, 4-8h, 8-24h, 24h+）をカバー"""
    from src.api.v1.reports import get_resolution_distribution

    incidents = [
        _make_incident(resolved_hours=0.5),   # 0-1h
        _make_incident(resolved_hours=2.0),   # 1-4h
        _make_incident(resolved_hours=5.0),   # 4-8h
        _make_incident(resolved_hours=12.0),  # 8-24h
        _make_incident(resolved_hours=30.0),  # 24h+
    ]
    db = _make_db_for_distribution(incidents)
    user = _make_user()

    result = await get_resolution_distribution(db=db, current_user=user, year=2026, month=1)

    buckets = result["buckets"]
    assert len(buckets) == 5
    assert buckets[0]["count"] == 1  # 0-1h
    assert buckets[1]["count"] == 1  # 1-4h
    assert buckets[2]["count"] == 1  # 4-8h
    assert buckets[3]["count"] == 1  # 8-24h
    assert buckets[4]["count"] == 1  # 24h+


async def test_resolution_distribution_boundary_values():
    """境界値: ちょうど1h, 4h, 8h, 24h"""
    from src.api.v1.reports import get_resolution_distribution

    incidents = [
        _make_incident(resolved_hours=1.0),   # 1-4h バケット
        _make_incident(resolved_hours=4.0),   # 4-8h バケット
        _make_incident(resolved_hours=8.0),   # 8-24h バケット
        _make_incident(resolved_hours=24.0),  # 24h+ バケット
    ]
    db = _make_db_for_distribution(incidents)
    user = _make_user()

    result = await get_resolution_distribution(db=db, current_user=user, year=2026, month=1)

    buckets = result["buckets"]
    assert buckets[0]["count"] == 0  # 0-1h: 該当なし
    assert buckets[1]["count"] == 1  # 1-4h: 1.0h
    assert buckets[2]["count"] == 1  # 4-8h: 4.0h
    assert buckets[3]["count"] == 1  # 8-24h: 8.0h
    assert buckets[4]["count"] == 1  # 24h+: 24.0h


async def test_resolution_distribution_empty():
    """解決済みなし → 全バケット 0"""
    from src.api.v1.reports import get_resolution_distribution

    db = _make_db_for_distribution([])
    user = _make_user()

    result = await get_resolution_distribution(db=db, current_user=user, year=2026, month=1)

    for b in result["buckets"]:
        assert b["count"] == 0


async def test_resolution_distribution_default_period():
    """year/month 未指定で現在月のデフォルト値が使われる"""
    from src.api.v1.reports import get_resolution_distribution

    db = _make_db_for_distribution([])
    user = _make_user()

    result = await get_resolution_distribution(db=db, current_user=user, year=None, month=None)

    assert "period" in result
    assert "year" in result["period"]
    assert "month" in result["period"]


# ─── get_monthly_summary テスト ────────────────────────────


async def test_get_monthly_summary_combined():
    """stats + distribution の統合（monthly_summary）をカバー"""
    from src.api.v1.reports import get_monthly_summary

    incidents = [
        _make_incident(resolved_hours=2.0, sla_breached=False, affected_service="Web"),
        _make_incident(resolved_hours=26.0, sla_breached=True, affected_service="DB"),
    ]
    changes = [_make_change()]

    # monthly_summary は get_stats と get_resolution_distribution を内部呼び出し
    # → 合計3回の DB execute が必要（stats用: inc+chg, dist用: inc）
    db = MagicMock()

    inc_scalars = MagicMock()
    inc_scalars.all.return_value = incidents
    inc_result = MagicMock()
    inc_result.scalars.return_value = inc_scalars

    chg_scalars = MagicMock()
    chg_scalars.all.return_value = changes
    chg_result = MagicMock()
    chg_result.scalars.return_value = chg_scalars

    inc_scalars2 = MagicMock()
    inc_scalars2.all.return_value = incidents
    inc_result2 = MagicMock()
    inc_result2.scalars.return_value = inc_scalars2

    db.execute = AsyncMock(side_effect=[inc_result, chg_result, inc_result2])

    user = _make_user()

    result = await get_monthly_summary(db=db, current_user=user, year=2026, month=1)

    assert "period" in result
    assert "incidents" in result
    assert "resolution_distribution" in result
    assert len(result["resolution_distribution"]) == 5
    # 26h+ → バケット[4]に1件
    assert result["resolution_distribution"][4]["count"] == 1
