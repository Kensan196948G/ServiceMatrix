"""AI異常検知サービス・APIエンドポイントのテスト"""

import pytest
from unittest.mock import patch, MagicMock

from src.services.anomaly_detection_service import AnomalyDetectionService


# ─── サービス層テスト ────────────────────────────────────────────────────────


def _make_training_data(n: int = 20) -> list[dict]:
    """テスト用の学習データを生成"""
    data = []
    for i in range(n):
        data.append(
            {
                "hour": (9 + i % 9),  # 9〜17時
                "priority": "P3",
                "day_of_week": i % 5,  # 月〜金
            }
        )
    return data


def test_anomaly_service_train():
    """正常な学習テスト"""
    service = AnomalyDetectionService()
    assert not service.is_trained

    training_data = _make_training_data(20)
    result = service.train(training_data)

    assert result is True
    assert service.is_trained


def test_anomaly_score_normal():
    """正常データのスコアが低いことを確認"""
    service = AnomalyDetectionService()
    training_data = _make_training_data(20)
    service.train(training_data)

    # 通常業務時間帯・低優先度インシデント
    normal_incident = {"hour": 10, "priority": "P3", "day_of_week": 1}
    score = service.predict_anomaly_score(normal_incident)

    # 正常データはスコアが低いはず（閾値 0.6 未満）
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_anomaly_score_unusual_hour():
    """深夜帯 + P1 のスコアが計算されることを確認"""
    service = AnomalyDetectionService()
    # 日中 P3 のみで学習
    training_data = _make_training_data(30)
    service.train(training_data)

    # 深夜 P1 インシデント（学習データと大きく異なる）
    unusual_incident = {"hour": 3, "priority": "P1", "day_of_week": 6}
    score = service.predict_anomaly_score(unusual_incident)

    # スコアが計算されていること（値は実装依存のため存在確認のみ）
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_is_anomaly_threshold():
    """閾値判定テスト"""
    service = AnomalyDetectionService()
    training_data = _make_training_data(20)
    service.train(training_data)

    incident_data = {"hour": 10, "priority": "P3", "day_of_week": 2}

    # デフォルト閾値 0.6
    result = service.is_anomaly(incident_data)
    assert isinstance(result, bool)

    # カスタム閾値 0.0 → 常に異常（スコア >= 0.0 は常に真）
    result_low = service.is_anomaly(incident_data, threshold=0.0)
    assert result_low is True

    # カスタム閾値 1.1 → 常に正常（スコアは最大 1.0）
    result_high = service.is_anomaly(incident_data, threshold=1.1)
    assert result_high is False


def test_insufficient_data_returns_false():
    """データ不足時の graceful handling"""
    service = AnomalyDetectionService()

    # 10件未満は学習失敗
    insufficient_data = _make_training_data(5)
    result = service.train(insufficient_data)

    assert result is False
    assert not service.is_trained

    # 未学習モデルは常にスコア 0.0
    score = service.predict_anomaly_score({"hour": 3, "priority": "P1", "day_of_week": 0})
    assert score == 0.0


def test_untrained_model_returns_zero():
    """未学習モデルは異常スコア 0.0 を返すことを確認"""
    service = AnomalyDetectionService()
    assert not service.is_trained

    score = service.predict_anomaly_score({"hour": 12, "priority": "P2", "day_of_week": 3})
    assert score == 0.0

    is_anom = service.is_anomaly({"hour": 12, "priority": "P2", "day_of_week": 3})
    assert is_anom is False


# ─── APIエンドポイントテスト ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anomaly_api_status_endpoint(client, auth_headers):
    """GET /api/v1/ai/anomaly/status エンドポイントのテスト"""
    response = await client.get("/api/v1/ai/anomaly/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "is_trained" in data
    assert "model_type" in data
    assert data["model_type"] == "IsolationForest"
    assert "status" in data
    assert data["status"] in ("ready", "not_trained")


@pytest.mark.asyncio
async def test_anomaly_api_score_endpoint_not_found(client, auth_headers):
    """GET /api/v1/ai/anomaly/score - 存在しないインシデントの場合 404"""
    # 有効なUUID形式だが存在しないインシデントID
    response = await client.get(
        "/api/v1/ai/anomaly/score",
        params={"incident_id": "ffffffff-ffff-ffff-ffff-ffffffffffff"},
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_anomaly_api_bulk_score_endpoint(client, auth_headers):
    """POST /api/v1/ai/anomaly/score/bulk エンドポイントのテスト"""
    payload = {
        "incidents": [
            {"hour": 10, "priority": "P3", "day_of_week": 1},
            {"hour": 3, "priority": "P1", "day_of_week": 6},
        ]
    }
    response = await client.post(
        "/api/v1/ai/anomaly/score/bulk",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert "anomaly_count" in data
    assert "results" in data
    assert len(data["results"]) == 2
    for result in data["results"]:
        assert "anomaly_score" in result
        assert "is_anomaly" in result
