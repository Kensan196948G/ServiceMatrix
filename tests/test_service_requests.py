"""サービスリクエスト管理テスト - ステータス遷移・採番"""
import re
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.service_request import VALID_SR_TRANSITIONS
from src.services.service_request_service import (
    _get_next_sr_number,
    create_service_request,
    get_service_requests,
    transition_service_request_status,
    update_service_request,
)


def test_sr_number_format():
    """SR-YYYY-NNNNNNフォーマットのパターン検証"""
    pattern = re.compile(r"^SR-\d{4}-\d{6}$")
    year = datetime.now(UTC).year
    sample = f"SR-{year}-000001"
    assert pattern.match(sample), f"フォーマット不正: {sample}"


def test_sr_valid_transitions_defined():
    """有効なステータス遷移が全ステータス分定義されていること"""
    expected_statuses = {
        "New", "Pending_Approval", "Approved", "In_Progress", "In_Fulfillment",
        "Fulfilled", "Failed", "Rejected", "Cancelled", "Closed"
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
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_sr))
    )
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
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_sr))
    )

    with pytest.raises(ValueError, match="遷移は許可されていません"):
        await transition_service_request_status(
            mock_db, mock_sr.request_id, "Fulfilled", None
        )


@pytest.mark.asyncio
async def test_sr_not_found_raises_value_error():
    """存在しないSRへの遷移でValueErrorが発生すること"""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    request_id = uuid.uuid4()
    with pytest.raises(ValueError, match="が見つかりません"):
        await transition_service_request_status(mock_db, request_id, "Fulfilled", None)


@pytest.mark.asyncio
async def test_get_next_sr_number_format():
    """_get_next_sr_numberが正しいフォーマットを返すこと"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_db.execute = AsyncMock(return_value=mock_result)

    sr_number = await _get_next_sr_number(mock_db)
    year = datetime.now(UTC).year
    assert sr_number == f"SR-{year}-000042"
    assert re.match(r"^SR-\d{4}-\d{6}$", sr_number)


@pytest.mark.asyncio
async def test_create_service_request():
    """create_service_requestがServiceRequestを返すこと"""
    mock_sr = MagicMock()
    mock_sr.request_id = uuid.uuid4()
    mock_sr.request_number = "SR-2025-000001"

    mock_db = AsyncMock()
    seq_result = MagicMock()
    seq_result.scalar_one.return_value = 1
    mock_db.execute = AsyncMock(return_value=seq_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

    with pytest.MonkeyPatch().context() as m:
        m.setattr(
            "src.services.service_request_service.audit_service.record_audit_log",
            AsyncMock(),
        )
        m.setattr(
            "src.services.service_request_service.ServiceRequest",
            MagicMock(return_value=mock_sr),
        )
        result = await create_service_request(mock_db, {"title": "Test SR"})

    assert result is mock_sr


@pytest.mark.asyncio
async def test_get_service_requests_with_status_filter():
    """statusフィルタを指定してget_service_requestsが動作すること"""
    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [MagicMock()]
    mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

    items, total = await get_service_requests(mock_db, status="New", skip=0, limit=10)
    assert total == 1
    assert len(items) == 1


@pytest.mark.asyncio
async def test_get_service_requests_no_filter():
    """statusフィルタなしでget_service_requestsが動作すること"""
    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 2
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
    mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

    items, total = await get_service_requests(mock_db, status=None, skip=0, limit=10)
    assert total == 2
    assert len(items) == 2


@pytest.mark.asyncio
async def test_update_service_request_not_found():
    """存在しないSRの更新でNoneを返すこと"""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    result = await update_service_request(mock_db, uuid.uuid4(), {"title": "Updated"})
    assert result is None


@pytest.mark.asyncio
async def test_update_service_request_success():
    """既存SRの更新が正常に動作すること"""
    mock_sr = MagicMock()
    mock_sr.request_id = uuid.uuid4()
    mock_sr.title = "Old Title"

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_sr))
    )
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    with pytest.MonkeyPatch().context() as m:
        m.setattr(
            "src.services.service_request_service.audit_service.record_audit_log",
            AsyncMock(),
        )
        result = await update_service_request(mock_db, mock_sr.request_id, {"title": "New Title"})

    assert result is mock_sr
