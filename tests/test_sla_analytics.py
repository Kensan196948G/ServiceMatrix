"""SLAアナリティクス API テスト - Issue #57

エンドポイント関数を直接呼び出してカバレッジを取得するパターン。
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.analytics import (
    change_trends,
    export_csv,
    sla_trends,
    summary_metrics,
)
from src.models.incident import Incident
from src.models.change import Change
from src.models.user import User, UserRole

pytestmark = pytest.mark.asyncio

NOW = datetime.now(UTC)


def _make_user(**overrides):
    defaults = {
        "user_id": uuid.uuid4(),
        "username": "testadmin",
        "email": "admin@test.com",
        "role": UserRole.SYSTEM_ADMIN,
        "is_active": True,
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_incident(**overrides):
    defaults = {
        "incident_id": uuid.uuid4(),
        "incident_number": f"INC-2026-{uuid.uuid4().hex[:6]}",
        "title": "Test incident",
        "priority": "P2",
        "status": "New",
        "sla_breached": False,
        "created_at": NOW,
        "department": "IT",
    }
    defaults.update(overrides)
    inc = MagicMock(spec=Incident)
    for k, v in defaults.items():
        setattr(inc, k, v)
    return inc


def _make_change(**overrides):
    defaults = {
        "change_id": uuid.uuid4(),
        "change_number": f"CHG-2026-{uuid.uuid4().hex[:6]}",
        "title": "Test change",
        "change_type": "Normal",
        "status": "Completed",
        "created_at": NOW,
    }
    defaults.update(overrides)
    chg = MagicMock(spec=Change)
    for k, v in defaults.items():
        setattr(chg, k, v)
    return chg


# ────────────────────────────────────────────────────────────────
# 1. SLAトレンドエンドポイント - 基本動作
# ────────────────────────────────────────────────────────────────
async def test_sla_trends_endpoint():
    """GET /api/v1/analytics/sla-trends が正常なレスポンスを返す"""
    user = _make_user()
    db = AsyncMock()

    incidents = [
        _make_incident(sla_breached=False),
        _make_incident(sla_breached=True),
        _make_incident(sla_breached=False),
    ]

    with patch(
        "src.api.v1.analytics.get_incident_sla_trends",
        new_callable=AsyncMock,
        return_value={
            "period_days": 30,
            "total_incidents": 3,
            "sla_breaches": 1,
            "sla_compliance_rate": 66.7,
            "daily_trends": [{"date": "2026-03-11", "count": 3, "breaches": 1}],
            "by_priority": {"P2": {"count": 3, "breaches": 1}},
        },
    ) as mock_fn:
        result = await sla_trends(
            current_user=user,
            db=db,
            days=30,
            department=None,
        )

    assert result["period_days"] == 30
    assert result["total_incidents"] == 3
    assert result["sla_breaches"] == 1
    assert "daily_trends" in result
    assert "by_priority" in result
    mock_fn.assert_awaited_once_with(db, days=30, department=None)


# ────────────────────────────────────────────────────────────────
# 2. 変更管理トレンドエンドポイント
# ────────────────────────────────────────────────────────────────
async def test_change_trends_endpoint():
    """GET /api/v1/analytics/change-trends が正常なレスポンスを返す"""
    user = _make_user()
    db = AsyncMock()

    with patch(
        "src.api.v1.analytics.get_change_success_trends",
        new_callable=AsyncMock,
        return_value={
            "period_days": 30,
            "total_changes": 10,
            "completed": 8,
            "failed": 1,
            "cancelled": 1,
            "in_progress": 0,
            "pending_approval": 0,
            "success_rate": 80.0,
            "daily_trends": [],
            "by_type": {"Normal": {"count": 10, "completed": 8, "failed": 1}},
        },
    ) as mock_fn:
        result = await change_trends(
            current_user=user,
            db=db,
            days=30,
        )

    assert result["period_days"] == 30
    assert result["total_changes"] == 10
    assert result["success_rate"] == 80.0
    assert "by_type" in result
    mock_fn.assert_awaited_once_with(db, days=30)


# ────────────────────────────────────────────────────────────────
# 3. サマリーメトリクスエンドポイント
# ────────────────────────────────────────────────────────────────
async def test_summary_metrics_endpoint():
    """GET /api/v1/analytics/summary が正常なレスポンスを返す"""
    user = _make_user()
    db = AsyncMock()

    with patch(
        "src.api.v1.analytics.get_summary_metrics",
        new_callable=AsyncMock,
        return_value={
            "open_incidents": 5,
            "active_sla_breaches": 2,
            "pending_changes": 3,
            "incidents_last_24h": 1,
            "open_p1_incidents": 0,
            "active_changes": 2,
            "generated_at": NOW.isoformat(),
        },
    ) as mock_fn:
        result = await summary_metrics(current_user=user, db=db)

    assert result["open_incidents"] == 5
    assert result["active_sla_breaches"] == 2
    assert result["pending_changes"] == 3
    assert "generated_at" in result
    mock_fn.assert_awaited_once_with(db)


# ────────────────────────────────────────────────────────────────
# 4. days パラメータが機能する
# ────────────────────────────────────────────────────────────────
async def test_sla_trends_with_days_param():
    """days=7 パラメータが get_incident_sla_trends に渡される"""
    user = _make_user()
    db = AsyncMock()

    with patch(
        "src.api.v1.analytics.get_incident_sla_trends",
        new_callable=AsyncMock,
        return_value={
            "period_days": 7,
            "total_incidents": 5,
            "sla_breaches": 0,
            "sla_compliance_rate": 100.0,
            "daily_trends": [],
            "by_priority": {},
        },
    ) as mock_fn:
        result = await sla_trends(
            current_user=user,
            db=db,
            days=7,
            department="Engineering",
        )

    assert result["period_days"] == 7
    mock_fn.assert_awaited_once_with(db, days=7, department="Engineering")


# ────────────────────────────────────────────────────────────────
# 5. CSV エクスポートエンドポイント
# ────────────────────────────────────────────────────────────────
async def test_csv_export_endpoint():
    """GET /api/v1/analytics/export/csv が CSV StreamingResponse を返す"""
    user = _make_user(role=UserRole.SERVICE_MANAGER)
    db = AsyncMock()

    with patch(
        "src.api.v1.analytics.get_incident_sla_trends",
        new_callable=AsyncMock,
        return_value={
            "period_days": 30,
            "total_incidents": 10,
            "sla_breaches": 1,
            "sla_compliance_rate": 90.0,
            "daily_trends": [
                {"date": "2026-03-01", "count": 5, "breaches": 0},
                {"date": "2026-03-02", "count": 5, "breaches": 1},
            ],
            "by_priority": {"P1": {"count": 2, "breaches": 1}},
        },
    ):
        response = await export_csv(current_user=user, db=db, days=30)

    # StreamingResponse であることを確認
    from fastapi.responses import StreamingResponse
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/csv"
    assert "sla_trends_30days.csv" in response.headers["content-disposition"]

    # CSVコンテンツ検証
    content = b""
    async for chunk in response.body_iterator:
        if isinstance(chunk, str):
            content += chunk.encode()
        else:
            content += chunk
    csv_text = content.decode()
    assert "date" in csv_text
    assert "count" in csv_text
    assert "breaches" in csv_text
    assert "2026-03-01" in csv_text


# ────────────────────────────────────────────────────────────────
# 6. レスポンス構造の確認
# ────────────────────────────────────────────────────────────────
async def test_analytics_response_structure():
    """SLAトレンドレスポンスが必須フィールドを持つ"""
    user = _make_user()
    db = AsyncMock()

    expected_keys = {
        "period_days",
        "total_incidents",
        "sla_breaches",
        "sla_compliance_rate",
        "daily_trends",
        "by_priority",
    }

    with patch(
        "src.api.v1.analytics.get_incident_sla_trends",
        new_callable=AsyncMock,
        return_value={
            "period_days": 30,
            "total_incidents": 0,
            "sla_breaches": 0,
            "sla_compliance_rate": 100.0,
            "daily_trends": [],
            "by_priority": {},
        },
    ):
        result = await sla_trends(
            current_user=user,
            db=db,
            days=30,
            department=None,
        )

    assert expected_keys.issubset(set(result.keys())), (
        f"Missing keys: {expected_keys - set(result.keys())}"
    )


# ────────────────────────────────────────────────────────────────
# 7. サービス関数の直接テスト - インシデントSLAトレンド集計
# ────────────────────────────────────────────────────────────────
async def test_sla_analytics_service_direct():
    """sla_analytics_service.get_incident_sla_trends をDBモックで直接テスト"""
    from src.services.sla_analytics_service import get_incident_sla_trends

    # テストデータ: 3件のインシデント（1件SLA違反）
    incidents = [
        _make_incident(sla_breached=False, priority="P1", created_at=NOW),
        _make_incident(sla_breached=True, priority="P2", created_at=NOW),
        _make_incident(sla_breached=False, priority="P2", created_at=NOW),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = incidents

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_incident_sla_trends(db, days=30)

    assert result["period_days"] == 30
    assert result["total_incidents"] == 3
    assert result["sla_breaches"] == 1
    assert result["sla_compliance_rate"] == pytest.approx(66.7, abs=0.1)
    assert "P1" in result["by_priority"]
    assert "P2" in result["by_priority"]
    assert result["by_priority"]["P1"]["count"] == 1
    assert result["by_priority"]["P2"]["count"] == 2


# ────────────────────────────────────────────────────────────────
# 8. サービス関数の直接テスト - 変更管理成功率集計
# ────────────────────────────────────────────────────────────────
async def test_change_success_trends_service_direct():
    """sla_analytics_service.get_change_success_trends をDBモックで直接テスト"""
    from src.services.sla_analytics_service import get_change_success_trends

    changes = [
        _make_change(status="Completed", change_type="Normal", created_at=NOW),
        _make_change(status="Completed", change_type="Standard", created_at=NOW),
        _make_change(status="Failed", change_type="Emergency", created_at=NOW),
        _make_change(status="Cancelled", change_type="Normal", created_at=NOW),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = changes

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_change_success_trends(db, days=30)

    assert result["period_days"] == 30
    assert result["total_changes"] == 4
    assert result["completed"] == 2
    assert result["failed"] == 1
    assert result["cancelled"] == 1
    assert result["success_rate"] == 50.0


# ────────────────────────────────────────────────────────────────
# 9. サービス関数の直接テスト - サマリーメトリクス
# ────────────────────────────────────────────────────────────────
async def test_summary_metrics_service_direct():
    """sla_analytics_service.get_summary_metrics をDBモックで直接テスト"""
    from src.services.sla_analytics_service import get_summary_metrics

    db = AsyncMock()

    # 各クエリのモック（順番に返す）
    call_count = [0]
    expected_scalars = [5, 2, 3, 1, 0, 2]

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar.return_value = expected_scalars[call_count[0] % len(expected_scalars)]
        call_count[0] += 1
        return mock_result

    db.execute = mock_execute

    result = await get_summary_metrics(db)

    assert "open_incidents" in result
    assert "active_sla_breaches" in result
    assert "pending_changes" in result
    assert "incidents_last_24h" in result
    assert "open_p1_incidents" in result
    assert "active_changes" in result
    assert "generated_at" in result
