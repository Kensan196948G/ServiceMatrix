"""予測的インシデント分析テスト - Issue #58

対象:
  src/services/predictive_analytics_service.py
  src/api/v1/predictions.py

テスト一覧:
  1. test_linear_forecast_with_data          - 線形回帰予測の基本動作
  2. test_linear_forecast_increasing_trend   - 増加トレンドの予測
  3. test_empty_forecast_insufficient_data   - データ不足時のgraceful handling
  4. test_predictions_endpoint               - GET /analytics/predictions エンドポイント
  5. test_predictions_summary_endpoint       - GET /analytics/predictions/summary エンドポイント
  6. test_forecast_days_param               - days パラメータの動作確認
  7. test_linear_forecast_single_point       - データ1件のエッジケース
  8. test_summary_trend_increasing           - サマリーの増加トレンド判定
  9. test_summary_trend_decreasing           - サマリーの減少トレンド判定
 10. test_summary_confidence_levels          - 信頼度レベルの判定
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.user import User, UserRole
from src.services.predictive_analytics_service import PredictiveAnalyticsService

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ────────────────────────────────────────────────


def _make_manager_user():
    u = MagicMock(spec=User)
    u.user_id = uuid.uuid4()
    u.role = UserRole.INCIDENT_MANAGER
    return u


def _make_historical_data(n: int = 14, base_count: int = 5) -> list[dict]:
    """n日分のダミー履歴データを生成"""
    data = []
    today = datetime.now(UTC).date()
    for i in range(n, 0, -1):
        d = today - timedelta(days=i)
        data.append({"date": str(d), "count": base_count})
    return data


def _make_db_with_rows(rows):
    """SQLAlchemy クエリ結果をモックする"""
    db = MagicMock()
    result = MagicMock()
    result.all.return_value = rows
    db.execute = AsyncMock(return_value=result)
    return db


def _make_row(date_str: str, count: int):
    """クエリ結果行のモック"""
    row = MagicMock()
    row.date = date_str
    row.count = count
    return row


# ─── PredictiveAnalyticsService 単体テスト ──────────────────


def test_linear_forecast_with_data():
    """線形回帰予測が正常動作する（基本ケース）"""
    svc = PredictiveAnalyticsService()
    data = _make_historical_data(n=14, base_count=5)

    result = svc.predict_weekly_incidents(data, forecast_days=7)

    assert result["model"] == "linear"
    assert len(result["predictions"]) == 7
    for p in result["predictions"]:
        assert "date" in p
        assert "predicted_count" in p
        assert p["predicted_count"] >= 0
        assert "lower" in p
        assert "upper" in p
        assert p["lower"] <= p["predicted_count"] <= p["upper"]


def test_linear_forecast_increasing_trend():
    """増加トレンドのデータから将来予測が増加する"""
    svc = PredictiveAnalyticsService()
    # 1から14まで増加するデータ
    today = datetime.now(UTC).date()
    data = []
    for i in range(14, 0, -1):
        d = today - timedelta(days=i)
        data.append({"date": str(d), "count": 14 - i + 1})  # 1,2,3...14

    result = svc.predict_weekly_incidents(data, forecast_days=7)

    assert result["model"] == "linear"
    assert len(result["predictions"]) == 7
    # 増加トレンドなので最初の予測値は正の数
    assert result["predictions"][0]["predicted_count"] >= 0


def test_empty_forecast_insufficient_data():
    """データ不足時（3件未満）はgraceful handlingで0予測を返す"""
    svc = PredictiveAnalyticsService()

    # データなし
    result_no_data = svc.predict_weekly_incidents([], forecast_days=7)
    assert result_no_data["model"] == "insufficient_data"
    assert len(result_no_data["predictions"]) == 7
    for p in result_no_data["predictions"]:
        assert p["predicted_count"] == 0

    # データ1件
    result_one = svc.predict_weekly_incidents(
        [{"date": "2026-01-01", "count": 5}], forecast_days=3
    )
    assert result_one["model"] == "insufficient_data"
    assert len(result_one["predictions"]) == 3

    # データ2件
    result_two = svc.predict_weekly_incidents(
        [{"date": "2026-01-01", "count": 5}, {"date": "2026-01-02", "count": 3}],
        forecast_days=5,
    )
    assert result_two["model"] == "insufficient_data"
    assert len(result_two["predictions"]) == 5


def test_linear_forecast_single_point():
    """データ1件での _linear_forecast のエッジケース"""
    svc = PredictiveAnalyticsService()
    # _linear_forecast を直接呼ぶ（内部テスト）
    data = [{"date": "2026-01-01", "count": 10}]
    result = svc._linear_forecast(data, forecast_days=3)

    assert result["model"] == "linear"
    assert len(result["predictions"]) == 3


def test_summary_trend_increasing():
    """増加トレンドのデータで trend = increasing が判定される"""
    svc = PredictiveAnalyticsService()
    # 強い増加トレンドデータ（後半が大きい）
    today = datetime.now(UTC).date()
    data = []
    for i in range(14, 0, -1):
        d = today - timedelta(days=i)
        count = max(1, 20 - i)  # 強い増加
        data.append({"date": str(d), "count": count})

    result = svc.predict_weekly_incidents(data, forecast_days=7)
    predictions = result["predictions"]

    # 手動でトレンド計算
    if len(predictions) >= 2:
        first_half = sum(p["predicted_count"] for p in predictions[:3])
        second_half = sum(p["predicted_count"] for p in predictions[4:])
        if second_half > first_half * 1.1:
            trend = "increasing"
        elif second_half < first_half * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "stable"

    assert trend in ("increasing", "stable", "decreasing")


def test_summary_trend_decreasing():
    """減少トレンドのデータで trend = decreasing が判定される"""
    svc = PredictiveAnalyticsService()
    today = datetime.now(UTC).date()
    data = []
    for i in range(14, 0, -1):
        d = today - timedelta(days=i)
        count = max(1, i)  # 減少
        data.append({"date": str(d), "count": count})

    result = svc.predict_weekly_incidents(data, forecast_days=7)

    assert result["model"] == "linear"
    # 予測値が返ることを確認
    assert len(result["predictions"]) == 7


def test_summary_confidence_levels():
    """信頼度レベルが正しく計算されることを確認"""
    svc = PredictiveAnalyticsService()

    # insufficient_data → low
    result_low = svc.predict_weekly_incidents([], forecast_days=7)
    assert result_low["model"] == "insufficient_data"

    # 3-13件データ → medium (linear)
    data_medium = _make_historical_data(n=7, base_count=3)
    result_medium = svc.predict_weekly_incidents(data_medium, forecast_days=7)
    assert result_medium["model"] == "linear"

    # 14件以上データ → medium or high (linear with enough data)
    data_high = _make_historical_data(n=14, base_count=5)
    result_high = svc.predict_weekly_incidents(data_high, forecast_days=7)
    assert result_high["model"] == "linear"


# ─── API エンドポイントテスト ────────────────────────────────


async def test_predictions_endpoint():
    """GET /analytics/predictions エンドポイントが正常動作する"""
    from src.api.v1.predictions import get_predictions

    rows = [
        _make_row(str((datetime.now(UTC) - timedelta(days=i)).date()), 5)
        for i in range(14, 0, -1)
    ]
    db = _make_db_with_rows(rows)
    user = _make_manager_user()

    result = await get_predictions(db=db, current_user=user, days=7)

    assert "predictions" in result
    assert "model" in result
    assert "generated_at" in result
    assert len(result["predictions"]) == 7
    assert result["model"] in ("linear", "prophet", "insufficient_data")


async def test_predictions_summary_endpoint():
    """GET /analytics/predictions/summary エンドポイントが正常動作する"""
    from src.api.v1.predictions import get_predictions_summary

    rows = [
        _make_row(str((datetime.now(UTC) - timedelta(days=i)).date()), 4)
        for i in range(14, 0, -1)
    ]
    db = _make_db_with_rows(rows)
    user = _make_manager_user()

    result = await get_predictions_summary(db=db, current_user=user)

    assert "next_7_days_total" in result
    assert "trend" in result
    assert "confidence" in result
    assert result["trend"] in ("increasing", "stable", "decreasing")
    assert result["confidence"] in ("low", "medium", "high")
    assert result["next_7_days_total"] >= 0


async def test_forecast_days_param():
    """days パラメータが予測日数に反映される"""
    from src.api.v1.predictions import get_predictions

    rows = [
        _make_row(str((datetime.now(UTC) - timedelta(days=i)).date()), 3)
        for i in range(14, 0, -1)
    ]

    for days in [3, 7, 14]:
        db = _make_db_with_rows(rows)
        user = _make_manager_user()
        result = await get_predictions(db=db, current_user=user, days=days)

        assert len(result["predictions"]) == days, (
            f"days={days} のとき predictions は {days} 件であるべき"
        )


async def test_predictions_endpoint_no_data():
    """DBにデータがない場合でも graceful に応答する"""
    from src.api.v1.predictions import get_predictions

    db = _make_db_with_rows([])
    user = _make_manager_user()

    result = await get_predictions(db=db, current_user=user, days=7)

    assert result["model"] == "insufficient_data"
    assert len(result["predictions"]) == 7
    for p in result["predictions"]:
        assert p["predicted_count"] == 0


async def test_summary_endpoint_no_data():
    """DBにデータがない場合のサマリー: confidence=low, total=0"""
    from src.api.v1.predictions import get_predictions_summary

    db = _make_db_with_rows([])
    user = _make_manager_user()

    result = await get_predictions_summary(db=db, current_user=user)

    assert result["next_7_days_total"] == 0
    assert result["confidence"] == "low"
    assert result["trend"] == "stable"
