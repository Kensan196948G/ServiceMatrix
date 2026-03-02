"""インシデント管理テスト - SLA・ステータス遷移"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.incident_service import (
    SLA_CONFIG,
    VALID_STATUS_TRANSITIONS,
    _calculate_sla_deadlines,
)


def test_sla_config_exists():
    """P1-P4のSLA設定が存在すること"""
    for priority in ["P1", "P2", "P3", "P4"]:
        assert priority in SLA_CONFIG
        assert "response_minutes" in SLA_CONFIG[priority]
        assert "resolution_minutes" in SLA_CONFIG[priority]


def test_sla_p1_strictest():
    """P1がP4より厳しいSLAを持つこと"""
    assert SLA_CONFIG["P1"]["response_minutes"] < SLA_CONFIG["P4"]["response_minutes"]
    assert SLA_CONFIG["P1"]["resolution_minutes"] < SLA_CONFIG["P4"]["resolution_minutes"]


def test_sla_p1_config():
    """P1 SLA: 応答15分・解決60分"""
    assert SLA_CONFIG["P1"]["response_minutes"] == 15
    assert SLA_CONFIG["P1"]["resolution_minutes"] == 60


def test_sla_p4_config():
    """P4 SLA: 応答480分・解決4320分"""
    assert SLA_CONFIG["P4"]["response_minutes"] == 480
    assert SLA_CONFIG["P4"]["resolution_minutes"] == 4320


def test_calculate_sla_deadlines_p1():
    """P1 SLA期限計算が正確であること"""
    now = datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc)
    deadlines = _calculate_sla_deadlines("P1", now)

    response_due = deadlines["sla_response_due_at"]
    resolution_due = deadlines["sla_resolution_due_at"]

    diff_response = (response_due - now).total_seconds() / 60
    diff_resolution = (resolution_due - now).total_seconds() / 60

    assert diff_response == 15.0
    assert diff_resolution == 60.0


def test_valid_status_transitions_new():
    """New状態からの有効な遷移"""
    assert "Acknowledged" in VALID_STATUS_TRANSITIONS["New"]
    assert "In_Progress" in VALID_STATUS_TRANSITIONS["New"]


def test_closed_state_no_transitions():
    """Closed状態からの遷移は不可"""
    assert len(VALID_STATUS_TRANSITIONS["Closed"]) == 0


def test_resolved_can_reopen():
    """Resolvedから再オープンできること"""
    assert "In_Progress" in VALID_STATUS_TRANSITIONS["Resolved"]


def test_valid_transitions_are_sets():
    """全ステータス遷移が集合型で定義されていること"""
    for transitions in VALID_STATUS_TRANSITIONS.values():
        assert isinstance(transitions, set)
