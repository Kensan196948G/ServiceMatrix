"""change_risk_service.py 未カバー行テスト

対象: src/services/change_risk_service.py (94%)
lines 54 (change not found), 133-135 (short description),
156-157 (emergency change rec), 160-161 (timing rec), 164-165 (history rec)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


async def test_assess_risk_change_not_found_raises_value_error():
    """assess_risk: change が None → ValueError（line 54）"""
    from src.services.change_risk_service import ChangeRiskService

    svc = ChangeRiskService()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(ValueError, match="Change not found"):
        await svc.assess_risk(db, str(uuid.uuid4()))


def test_score_description_detail_none_description_adds_score():
    """_score_description_detail: description が None → score += 10（lines 133-135）"""
    from src.services.change_risk_service import ChangeRiskService

    svc = ChangeRiskService()
    factor = svc._score_description_detail(None, "テスト計画あり")

    assert factor.score >= 10
    assert "不十分" in factor.description or "説明" in factor.description


def test_score_description_detail_short_description_adds_score():
    """_score_description_detail: 短い説明（<50文字）→ score += 10（lines 133-135）"""
    from src.services.change_risk_service import ChangeRiskService

    svc = ChangeRiskService()
    factor = svc._score_description_detail("短い説明", "テスト計画あり")

    assert factor.score >= 10
    assert "不十分" in factor.description


def test_score_description_detail_sufficient_description_no_score():
    """_score_description_detail: 十分な説明（>=50文字）→ description スコアなし"""
    from src.services.change_risk_service import ChangeRiskService

    svc = ChangeRiskService()
    # 50文字以上の説明（ASCII文字で確実に50文字以上）
    long_desc = "This is a detailed change description that is longer than fifty characters for testing purposes."
    factor = svc._score_description_detail(long_desc, "テスト計画あり")

    # description は十分なので description 部分のスコアは加算されない（test_plan もあるので 0）
    assert factor.score == 0


def test_generate_recommendations_emergency_change():
    """_generate_recommendations: change_type スコア >= 25 → 緊急変更推奨（line 156-157）"""
    from src.services.change_risk_service import ChangeRiskService, RiskFactor

    svc = ChangeRiskService()
    factors = [
        RiskFactor("change_type", 25, "Emergency変更"),
        RiskFactor("timing", 0, "営業時間内作業"),
        RiskFactor("historical_failure", 0, "直近30日の同種別失敗件数: 0件"),
        RiskFactor("description_detail", 0, "説明・テスト計画あり"),
    ]
    recs = svc._generate_recommendations(factors, "High")

    assert any("緊急変更" in r for r in recs)


def test_generate_recommendations_timing_score_positive():
    """_generate_recommendations: timing スコア > 0 → メンテナンスウィンドウ推奨（line 160-161）"""
    from src.services.change_risk_service import ChangeRiskService, RiskFactor

    svc = ChangeRiskService()
    factors = [
        RiskFactor("change_type", 0, "Standard変更"),
        RiskFactor("timing", 5, "実施予定日時未設定"),
        RiskFactor("historical_failure", 0, "直近30日の同種別失敗件数: 0件"),
        RiskFactor("description_detail", 0, "説明・テスト計画あり"),
    ]
    recs = svc._generate_recommendations(factors, "Low")

    assert any("メンテナンスウィンドウ" in r for r in recs)


def test_generate_recommendations_high_history_score():
    """_generate_recommendations: history スコア >= 9 → ロールバック計画推奨（line 164-165）"""
    from src.services.change_risk_service import ChangeRiskService, RiskFactor

    svc = ChangeRiskService()
    factors = [
        RiskFactor("change_type", 0, "Standard変更"),
        RiskFactor("timing", 0, "営業時間内作業"),
        RiskFactor("historical_failure", 9, "直近30日の同種別失敗件数: 3件"),
        RiskFactor("description_detail", 0, "説明・テスト計画あり"),
    ]
    recs = svc._generate_recommendations(factors, "Medium")

    assert any("ロールバック" in r for r in recs)


def test_score_description_detail_no_test_plan_adds_score():
    """_score_description_detail: test_plan が None → score += 5（lines 137-138）"""
    from src.services.change_risk_service import ChangeRiskService

    svc = ChangeRiskService()
    # description は十分だが test_plan が None → line 137-138 実行
    long_desc = "This is a detailed change description that is longer than fifty characters for testing purposes."
    factor = svc._score_description_detail(long_desc, None)

    assert factor.score == 5
    assert "テスト計画未設定" in factor.description


def test_generate_recommendations_no_test_plan_detail():
    """_generate_recommendations: detail.description に 'テスト計画未設定' → テスト計画推奨（line 169）"""
    from src.services.change_risk_service import ChangeRiskService, RiskFactor

    svc = ChangeRiskService()
    factors = [
        RiskFactor("change_type", 0, "Standard変更"),
        RiskFactor("timing", 0, "営業時間内作業"),
        RiskFactor("historical_failure", 0, "直近30日の同種別失敗件数: 0件"),
        RiskFactor("description_detail", 5, "テスト計画未設定"),
    ]
    recs = svc._generate_recommendations(factors, "Low")

    assert any("テスト計画を追加" in r for r in recs)


def test_generate_recommendations_no_special_conditions():
    """_generate_recommendations: 全スコア低 → 緊急変更・ウィンドウ・ロールバック推奨なし"""
    from src.services.change_risk_service import ChangeRiskService, RiskFactor

    svc = ChangeRiskService()
    factors = [
        RiskFactor("change_type", 10, "Normal変更"),
        RiskFactor("timing", 0, "営業時間内作業"),
        RiskFactor("historical_failure", 0, "直近30日の同種別失敗件数: 0件"),
        RiskFactor("description_detail", 0, "説明・テスト計画あり"),
    ]
    recs = svc._generate_recommendations(factors, "Low")

    assert not any("緊急変更" in r for r in recs)
    assert not any("メンテナンスウィンドウ" in r for r in recs)
    assert not any("ロールバック" in r for r in recs)
