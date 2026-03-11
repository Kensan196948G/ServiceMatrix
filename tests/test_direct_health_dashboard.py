"""health.py / dashboard.py / logging.py / rate_limit.py 直接呼び出しテスト

対象: src/api/v1/health.py (74%), src/api/v1/dashboard.py (73%),
      src/core/logging.py (67%), src/middleware/rate_limit.py (68%)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── health.py ───────────────────────────────────────────────────────────────


async def test_health_check_db_ok():
    """health_check: DB接続成功 → status=ok"""
    from src.api.v1.health import health_check

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())

    result = await health_check(db=db)

    assert result["status"] == "ok"
    assert result["database"] == "ok"


async def test_health_check_db_error():
    """health_check: DB接続失敗 → status=degraded（except分岐 lines 23-24）"""
    from src.api.v1.health import health_check

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("DB接続エラー"))

    result = await health_check(db=db)

    assert result["status"] == "degraded"
    assert result["database"] == "error"


async def test_get_metrics_json():
    """get_metrics_json: metrics.to_json() を返す"""
    from src.api.v1.health import get_metrics_json

    result = await get_metrics_json()

    assert isinstance(result, dict)


async def test_get_metrics_prometheus():
    """get_metrics_prometheus: PlainTextResponse を返す"""
    from fastapi.responses import PlainTextResponse

    from src.api.v1.health import get_metrics_prometheus

    result = await get_metrics_prometheus()

    assert isinstance(result, PlainTextResponse)


async def test_detailed_health_db_ok():
    """detailed_health: DB接続成功 → status=healthy（lines 49, 53）"""
    from src.api.v1.health import detailed_health

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db_read = AsyncMock()
    db_read.execute = AsyncMock(return_value=MagicMock())

    result = await detailed_health(db=db, db_read=db_read)

    assert result["status"] == "healthy"
    assert result["services"]["database"] == "connected"


async def test_detailed_health_db_error():
    """detailed_health: DB接続失敗 → status=degraded（lines 50-51）"""
    from src.api.v1.health import detailed_health

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("タイムアウト"))
    db_read = AsyncMock()
    db_read.execute = AsyncMock(return_value=MagicMock())

    result = await detailed_health(db=db, db_read=db_read)

    assert result["status"] == "degraded"
    assert result["services"]["database"] == "error"
    assert result["services"]["api"] == "up"


# ─── dashboard.py ─────────────────────────────────────────────────────────────


async def test_get_widgets_known_role():
    """get_widgets: 既知ロール → 対応ウィジェットを返す（lines 27-29）"""
    from src.api.v1.dashboard import get_widgets

    current_user = MagicMock()
    result = await get_widgets(current_user=current_user, role="OPERATOR")

    assert result["role"] == "OPERATOR"
    assert "sla_alerts" in result["widgets"]


async def test_get_widgets_case_insensitive():
    """get_widgets: ロール名は大文字化して照合"""
    from src.api.v1.dashboard import get_widgets

    current_user = MagicMock()
    result = await get_widgets(current_user=current_user, role="system_admin")

    assert result["role"] == "SYSTEM_ADMIN"
    assert "audit_summary" in result["widgets"]


async def test_get_widgets_unknown_role_falls_back_to_viewer():
    """get_widgets: 未知ロール → VIEWER のウィジェット"""
    from src.api.v1.dashboard import get_widgets

    current_user = MagicMock()
    result = await get_widgets(current_user=current_user, role="UNKNOWN_ROLE")

    assert result["role"] == "UNKNOWN_ROLE"
    assert "open_incidents" in result["widgets"]


async def test_get_widgets_all_roles():
    """get_widgets: 全ロールで返り値を確認"""
    from src.api.v1.dashboard import get_widgets

    current_user = MagicMock()
    for role in ["OPERATOR", "SERVICE_MANAGER", "CHANGE_MANAGER", "SYSTEM_ADMIN", "VIEWER"]:
        result = await get_widgets(current_user=current_user, role=role)
        assert result["role"] == role
        assert isinstance(result["widgets"], list)
        assert len(result["widgets"]) > 0


# ─── logging.py ───────────────────────────────────────────────────────────────


def test_setup_logging_runs_without_error():
    """setup_logging: 例外なく実行できる（lines 12-32）"""
    from src.core.logging import setup_logging

    setup_logging()  # 再呼び出しでも安全


def test_get_logger_returns_logger():
    """get_logger: ロガーオブジェクトを返す（line 35-36）"""
    from src.core.logging import get_logger

    logger = get_logger("test.module")
    assert logger is not None


# ─── rate_limit.py ────────────────────────────────────────────────────────────


async def test_rate_limit_non_local_ip_passes():
    """RateLimitMiddleware: 外部IPは通常処理される（lines 23-35）"""
    from src.middleware.rate_limit import RateLimitMiddleware

    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, calls=10, period=60)

    request = MagicMock()
    request.client.host = "192.168.1.100"

    response_mock = MagicMock()
    call_next = AsyncMock(return_value=response_mock)

    result = await middleware.dispatch(request, call_next)

    call_next.assert_called_once_with(request)
    assert result is response_mock


async def test_rate_limit_exceeded_raises_429():
    """RateLimitMiddleware: 制限超過 → 429エラー（lines 29-33）"""
    from fastapi import HTTPException

    from src.middleware.rate_limit import RateLimitMiddleware

    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, calls=2, period=60)

    request = MagicMock()
    request.client.host = "10.0.0.1"

    call_next = AsyncMock(return_value=MagicMock())

    # 2回は通過
    await middleware.dispatch(request, call_next)
    await middleware.dispatch(request, call_next)

    # 3回目は429
    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(request, call_next)

    assert exc_info.value.status_code == 429


async def test_rate_limit_testclient_skips():
    """RateLimitMiddleware: testclient IPはスキップ（line 21）"""
    from src.middleware.rate_limit import RateLimitMiddleware

    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, calls=1, period=60)

    request = MagicMock()
    request.client.host = "testclient"

    call_next = AsyncMock(return_value=MagicMock())

    # calls=1 でも testclient は何回でも通過
    await middleware.dispatch(request, call_next)
    await middleware.dispatch(request, call_next)
    await middleware.dispatch(request, call_next)

    assert call_next.call_count == 3


async def test_rate_limit_no_client_skips():
    """RateLimitMiddleware: client=None(unknown)はスキップ"""
    from src.middleware.rate_limit import RateLimitMiddleware

    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, calls=1, period=60)

    request = MagicMock()
    request.client = None

    call_next = AsyncMock(return_value=MagicMock())

    result = await middleware.dispatch(request, call_next)
    call_next.assert_called_once()
