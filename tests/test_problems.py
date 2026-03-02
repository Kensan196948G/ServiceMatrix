"""問題管理テスト - FSM遷移・Known Error DB・スキーマバリデーション"""
import re

import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock

from src.services.problem_service import (
    VALID_PROBLEM_TRANSITIONS,
    mark_as_known_error,
)
from src.schemas.problem import ProblemCreate


# ─── FSMステータス遷移テスト ─────────────────────────────────

def test_valid_problem_transitions_defined():
    """全ステータスのFSM遷移が定義されていること"""
    expected_statuses = {"New", "Under_Investigation", "Known_Error", "Resolved", "Closed"}
    assert set(VALID_PROBLEM_TRANSITIONS.keys()) == expected_statuses


def test_new_to_under_investigation():
    """New→Under_Investigation遷移が有効"""
    assert "Under_Investigation" in VALID_PROBLEM_TRANSITIONS["New"]


def test_closed_state_is_terminal():
    """Closed状態は終端（遷移なし）"""
    assert len(VALID_PROBLEM_TRANSITIONS["Closed"]) == 0


def test_resolved_can_reopen():
    """Resolved→Under_Investigationへ再調査可能"""
    assert "Under_Investigation" in VALID_PROBLEM_TRANSITIONS["Resolved"]


def test_under_investigation_to_known_error():
    """Under_Investigation→Known_Error遷移が有効"""
    assert "Known_Error" in VALID_PROBLEM_TRANSITIONS["Under_Investigation"]


def test_known_error_to_resolved():
    """Known_Error→Resolved遷移が有効"""
    assert "Resolved" in VALID_PROBLEM_TRANSITIONS["Known_Error"]


# ─── Known Error DBテスト ────────────────────────────────────

@pytest.mark.asyncio
async def test_known_error_requires_workaround():
    """ワークアラウンドが空文字列だとValueError"""
    mock_db = AsyncMock()
    mock_problem = MagicMock()
    mock_problem.status = "Under_Investigation"

    with pytest.raises(ValueError, match="ワークアラウンド"):
        await mark_as_known_error(mock_db, mock_problem, "")


@pytest.mark.asyncio
async def test_known_error_requires_non_empty_workaround():
    """空白文字列のみのワークアラウンドもValueError"""
    mock_db = AsyncMock()
    mock_problem = MagicMock()
    mock_problem.status = "Under_Investigation"

    with pytest.raises(ValueError, match="ワークアラウンド"):
        await mark_as_known_error(mock_db, mock_problem, "   ")


@pytest.mark.asyncio
async def test_known_error_sets_status():
    """mark_as_known_error後にstatus='Known_Error'になること"""
    mock_db = AsyncMock()
    mock_problem = MagicMock()
    mock_problem.status = "Under_Investigation"

    result = await mark_as_known_error(mock_db, mock_problem, "サーバー再起動で回復")

    assert mock_problem.status == "Known_Error"
    assert mock_problem.known_error is True
    assert mock_problem.workaround == "サーバー再起動で回復"


# ─── 問題番号フォーマットテスト ──────────────────────────────

def test_problem_number_format():
    """PRB-YYYY-NNNNNNパターンの正規表現検証"""
    pattern = re.compile(r"^PRB-\d{4}-\d{6}$")
    assert pattern.match("PRB-2026-000001")
    assert pattern.match("PRB-2025-123456")
    assert not pattern.match("INC-2026-000001")
    assert not pattern.match("PRB-26-000001")
    assert not pattern.match("PRB-2026-00001")


# ─── スキーマバリデーションテスト ────────────────────────────

def test_problem_create_valid_priorities():
    """P1-P4が有効なpriorityであること"""
    for p in ["P1", "P2", "P3", "P4"]:
        schema = ProblemCreate(title="テスト問題", priority=p)
        assert schema.priority == p


def test_problem_create_invalid_priority():
    """P5はinvalidなpriority"""
    with pytest.raises(ValidationError):
        ProblemCreate(title="テスト問題", priority="P5")


# ─── 追加テスト ──────────────────────────────────────────────

def test_transitions_are_sets():
    """全遷移がset型であること"""
    for status, transitions in VALID_PROBLEM_TRANSITIONS.items():
        assert isinstance(transitions, set), f"{status}の遷移がset型ではない"


def test_new_cannot_skip_to_resolved():
    """New→Resolvedへの直接遷移は許可されていない"""
    assert "Resolved" not in VALID_PROBLEM_TRANSITIONS["New"]
