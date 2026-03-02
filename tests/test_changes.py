"""変更管理テスト - リスクスコア・CAB承認フロー"""
import pytest
from src.services.change_service import (
    calculate_risk_score,
    VALID_CHANGE_TRANSITIONS,
    CAB_REQUIRED_TYPES,
    IMPACT_SCORES,
    URGENCY_SCORES,
    CHANGE_TYPE_SCORES,
)


def test_risk_score_scores_defined():
    """全スコアテーブルが定義されていること"""
    assert "Low" in IMPACT_SCORES
    assert "High" in IMPACT_SCORES
    assert "Emergency" in CHANGE_TYPE_SCORES
    assert "Standard" in URGENCY_SCORES or "Low" in URGENCY_SCORES


def test_risk_score_emergency_high():
    """Emergency/High/High は高リスクになること"""
    score, level = calculate_risk_score("Emergency", "High", "High")
    assert score >= 70
    assert level in ("High", "Critical")


def test_risk_score_standard_low():
    """Standard/Low/Low は低リスクになること"""
    score, level = calculate_risk_score("Standard", "Low", "Low")
    assert score <= 30
    assert level in ("Low", "Medium")


def test_risk_score_max_100():
    """リスクスコアの上限は100"""
    score, _ = calculate_risk_score("Emergency", "High", "High")
    assert score <= 100


def test_risk_score_non_negative():
    """リスクスコアは非負"""
    score, _ = calculate_risk_score("Standard", "Low", "Low")
    assert score >= 0


def test_cab_required_types():
    """CAB承認必須タイプが定義されていること"""
    assert "Normal" in CAB_REQUIRED_TYPES
    assert "Emergency" in CAB_REQUIRED_TYPES
    assert "Major" in CAB_REQUIRED_TYPES
    assert "Standard" not in CAB_REQUIRED_TYPES


def test_valid_change_transitions_draft():
    """Draft状態からSubmittedへ遷移できること"""
    assert "Submitted" in VALID_CHANGE_TRANSITIONS["Draft"]


def test_valid_change_transitions_completed():
    """Completed状態は終端（遷移なし）"""
    assert len(VALID_CHANGE_TRANSITIONS["Completed"]) == 0


def test_valid_change_transitions_cancelled():
    """Cancelled状態は終端（遷移なし）"""
    assert len(VALID_CHANGE_TRANSITIONS["Cancelled"]) == 0


def test_cab_review_leads_to_approved_or_rejected():
    """CAB_ReviewからApprovedまたはRejectedへ遷移できること"""
    transitions = VALID_CHANGE_TRANSITIONS["CAB_Review"]
    assert "Approved" in transitions
    assert "Rejected" in transitions
