"""SLA API エンドポイント直接呼び出しユニットテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.sla import (
    get_sla_status,
    get_sla_summary,
    list_sla_breaches,
    list_sla_warnings,
    manual_sla_check,
)

pytestmark = pytest.mark.asyncio

NOW = datetime.now(UTC)


# --- get_sla_summary() テスト ---------------------------------------------------


async def test_get_sla_summary_cache_miss():
    """get_sla_summary() キャッシュミス: サービス層呼び出し"""
    db = AsyncMock()
    mock_result = {"P1": {"total": 5, "breached": 1, "compliance_rate": 80.0}}

    with (
        patch("src.api.v1.sla.cache_get", new_callable=AsyncMock, return_value=None),
        patch("src.api.v1.sla.cache_set", new_callable=AsyncMock) as mock_set,
        patch(
            "src.api.v1.sla.sla_monitor.get_sla_summary",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
    ):
        result = await get_sla_summary(db=db)

    assert result == mock_result
    mock_set.assert_awaited_once()


async def test_get_sla_summary_cache_hit():
    """get_sla_summary() キャッシュヒット: キャッシュから返す（line 29）"""
    db = AsyncMock()
    cached_data = {"P1": {"total": 3, "breached": 0, "compliance_rate": 100.0}}

    with (
        patch(
            "src.api.v1.sla.cache_get",
            new_callable=AsyncMock,
            return_value=json.dumps(cached_data),
        ),
    ):
        result = await get_sla_summary(db=db)

    assert result == cached_data


# --- list_sla_warnings() テスト --------------------------------------------------


async def test_list_sla_warnings_empty():
    """list_sla_warnings() 空リスト（lines 41-42）"""
    db = AsyncMock()

    with patch(
        "src.api.v1.sla.sla_monitor.get_active_warnings",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await list_sla_warnings(db=db)

    assert result["warnings"] == []
    assert result["count"] == 0


async def test_list_sla_warnings_with_data():
    """list_sla_warnings() データあり"""
    db = AsyncMock()
    mock_warnings = [
        {
            "incident_id": str(uuid.uuid4()),
            "incident_number": "INC-2024-000001",
            "title": "Test",
            "priority": "P1",
            "sla_type": "resolution",
            "warning_level": "warning_70",
            "progress_percent": 75.0,
            "deadline": NOW.isoformat(),
        }
    ]

    with patch(
        "src.api.v1.sla.sla_monitor.get_active_warnings",
        new_callable=AsyncMock,
        return_value=mock_warnings,
    ):
        result = await list_sla_warnings(db=db)

    assert result["count"] == 1
    assert len(result["warnings"]) == 1


# --- list_sla_breaches() テスト --------------------------------------------------


async def test_list_sla_breaches_empty():
    """list_sla_breaches() 空リスト（lines 59-60）"""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    db.execute = AsyncMock(return_value=mock_result)

    result = await list_sla_breaches(db=db, skip=0, limit=50)

    assert result == []


async def test_list_sla_breaches_with_data():
    """list_sla_breaches() データあり"""
    db = AsyncMock()
    mock_incident = MagicMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_incident]
    mock_result.scalars.return_value = mock_scalars
    db.execute = AsyncMock(return_value=mock_result)

    result = await list_sla_breaches(db=db, skip=0, limit=50)

    assert len(result) == 1


# --- get_sla_status() テスト -----------------------------------------------------


async def test_get_sla_status_found():
    """get_sla_status() インシデント見つかる（lines 69, 72）"""
    db = AsyncMock()
    mock_status = {
        "incident_id": str(uuid.uuid4()),
        "incident_number": "INC-2024-000001",
        "priority": "P1",
        "status": "In_Progress",
        "sla_breached": False,
    }

    with patch(
        "src.api.v1.sla.sla_monitor.get_sla_status",
        new_callable=AsyncMock,
        return_value=mock_status,
    ):
        result = await get_sla_status(incident_id="test-id", db=db)

    assert result == mock_status


async def test_get_sla_status_not_found():
    """get_sla_status() インシデント見つからない -> 404（lines 70-71）"""
    from fastapi import HTTPException

    db = AsyncMock()

    with (
        patch(
            "src.api.v1.sla.sla_monitor.get_sla_status",
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_sla_status(incident_id="nonexistent", db=db)

    assert exc_info.value.status_code == 404


# --- manual_sla_check() テスト ---------------------------------------------------


async def test_manual_sla_check():
    """manual_sla_check() 正常実行"""
    db = AsyncMock()

    with (
        patch(
            "src.api.v1.sla.sla_monitor.check_sla_breaches",
            new_callable=AsyncMock,
            return_value=2,
        ),
        patch(
            "src.api.v1.sla.sla_monitor.check_sla_warnings",
            new_callable=AsyncMock,
            return_value=[{"incident_id": "x"}],
        ),
    ):
        result = await manual_sla_check(db=db)

    assert result["checked"] is True
    assert result["breaches_detected"] == 2
    assert result["warnings_detected"] == 1
    assert "timestamp" in result
