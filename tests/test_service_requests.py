"""サービスリクエスト管理テスト - ステータス遷移・採番"""
import re
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.service_request import VALID_SR_TRANSITIONS
from src.services.service_request_service import transition_service_request_status


def test_sr_number_format():
    """SR-YYYY-NNNNNNフォーマットのパターン検証"""
    pattern = re.compile(r"^SR-\d{4}-\d{6}$")
    year = datetime.now(UTC).year
    sample = f"SR-{year}-000001"
    assert pattern.match(sample), f"フォーマット不正: {sample}"


def test_sr_valid_transitions_defined():
    """有効なステータス遷移が全ステータス分定義されていること"""
    expected_statuses = {
        "New", "Pending_Approval", "Approved", "In_Progress",
        "Fulfilled", "Rejected", "Cancelled"
    }
    assert expected_statuses == set(VALID_SR_TRANSITIONS.keys())
    for transitions in VALID_SR_TRANSITIONS.values():
        assert isinstance(transitions, set)


def test_sr_new_to_pending_approval():
    """New → Pending_Approval 遷移が許可されていること"""
    assert "Pending_Approval" in VALID_SR_TRANSITIONS["New"]


def test_sr_new_to_in_progress():
    """New → In_Progress 遷移が許可されていること"""
    assert "In_Progress" in VALID_SR_TRANSITIONS["New"]


def test_sr_pending_to_approved():
    """Pending_Approval → Approved 遷移が許可されていること"""
    assert "Approved" in VALID_SR_TRANSITIONS["Pending_Approval"]


def test_sr_pending_to_rejected():
    """Pending_Approval → Rejected 遷移が許可されていること"""
    assert "Rejected" in VALID_SR_TRANSITIONS["Pending_Approval"]


def test_sr_approved_to_in_progress():
    """Approved → In_Progress 遷移が許可されていること"""
    assert "In_Progress" in VALID_SR_TRANSITIONS["Approved"]


def test_sr_in_progress_to_fulfilled():
    """In_Progress → Fulfilled 遷移が許可されていること"""
    assert "Fulfilled" in VALID_SR_TRANSITIONS["In_Progress"]


@pytest.mark.asyncio
async def test_sr_fulfilled_sets_fulfilled_at():
    """Fulfilled遷移時にfulfilled_atが設定されること"""
    mock_sr = MagicMock()
    mock_sr.request_id = uuid.uuid4()
    mock_sr.status = "In_Progress"
    mock_sr.fulfilled_at = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_sr)))
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    with pytest.MonkeyPatch().context() as m:
        m.setattr(
            "src.services.service_request_service.audit_service.record_audit_log",
            AsyncMock(),
        )
        result = await transition_service_request_status(
            mock_db, mock_sr.request_id, "Fulfilled", None
        )

    assert result.status == "Fulfilled"
    assert result.fulfilled_at is not None


@pytest.mark.asyncio
async def test_sr_invalid_transition():
    """無効なステータス遷移がValueErrorを発生させること"""
    mock_sr = MagicMock()
    mock_sr.request_id = uuid.uuid4()
    mock_sr.status = "New"

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_sr)))

    with pytest.raises(ValueError, match="遷移は許可されていません"):
        await transition_service_request_status(
            mock_db, mock_sr.request_id, "Fulfilled", None
        )
