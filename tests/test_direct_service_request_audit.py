"""service_request_service.py 監査ログ呼び出し直接テスト

対象:
  src/services/service_request_service.py (92%)
  lines 140-177: submit_request / approve_request / reject_request の audit_service 呼び出し
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _make_sr_mock(request_id=None, status="New"):
    sr = MagicMock()
    sr.request_id = request_id or uuid.uuid4()
    sr.request_number = "SR-2026-000001"
    sr.status = status
    return sr


# ─── submit_request (lines 135-147) ───────────────────────────────────────────


async def test_submit_request_calls_audit_log():
    """submit_request: audit_service.record_audit_log が SUBMIT アクションで呼ばれる"""
    from src.services.service_request_service import submit_request

    sr_mock = _make_sr_mock(status="Pending_Approval")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ) as mock_transition, patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        result = await submit_request(db, sr_mock.request_id, "user123")

    mock_transition.assert_called_once_with(db, sr_mock.request_id, "Pending_Approval", None)
    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["action"] == "SUBMIT"
    assert call_kwargs[1]["resource_type"] == "ServiceRequest"
    assert "submitted_by" in call_kwargs[1]["new_values"]
    assert call_kwargs[1]["new_values"]["submitted_by"] == "user123"
    assert result is sr_mock


async def test_submit_request_resource_id_matches_sr():
    """submit_request: resource_id が sr.request_id の文字列と一致する"""
    from src.services.service_request_service import submit_request

    rid = uuid.uuid4()
    sr_mock = _make_sr_mock(request_id=rid, status="Pending_Approval")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ), patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        await submit_request(db, rid, "submitter_user")

    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["resource_id"] == str(rid)


async def test_submit_request_returns_sr_object():
    """submit_request: ServiceRequest オブジェクトを返す"""
    from src.services.service_request_service import submit_request

    sr_mock = _make_sr_mock(status="Pending_Approval")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ), patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ):
        result = await submit_request(db, sr_mock.request_id, "user")

    assert result is sr_mock


# ─── approve_request (lines 150-162) ──────────────────────────────────────────


async def test_approve_request_calls_audit_log():
    """approve_request: audit_service.record_audit_log が APPROVE アクションで呼ばれる"""
    from src.services.service_request_service import approve_request

    sr_mock = _make_sr_mock(status="Approved")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ) as mock_transition, patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        result = await approve_request(db, sr_mock.request_id, "manager01", "承認します")

    mock_transition.assert_called_once_with(db, sr_mock.request_id, "Approved", "承認します")
    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["action"] == "APPROVE"
    assert call_kwargs[1]["resource_type"] == "ServiceRequest"
    assert call_kwargs[1]["new_values"]["approved_by"] == "manager01"
    assert call_kwargs[1]["new_values"]["comment"] == "承認します"
    assert result is sr_mock


async def test_approve_request_default_comment():
    """approve_request: comment デフォルト値（空文字）"""
    from src.services.service_request_service import approve_request

    sr_mock = _make_sr_mock(status="Approved")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ) as mock_transition, patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        await approve_request(db, sr_mock.request_id, "manager02")

    mock_transition.assert_called_once_with(db, sr_mock.request_id, "Approved", "")
    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["new_values"]["comment"] == ""


async def test_approve_request_resource_id_matches_sr():
    """approve_request: resource_id が sr.request_id の文字列と一致する"""
    from src.services.service_request_service import approve_request

    rid = uuid.uuid4()
    sr_mock = _make_sr_mock(request_id=rid, status="Approved")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ), patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        await approve_request(db, rid, "approver")

    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["resource_id"] == str(rid)


# ─── reject_request (lines 165-177) ───────────────────────────────────────────


async def test_reject_request_calls_audit_log():
    """reject_request: audit_service.record_audit_log が REJECT アクションで呼ばれる"""
    from src.services.service_request_service import reject_request

    sr_mock = _make_sr_mock(status="Rejected")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ) as mock_transition, patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        result = await reject_request(db, sr_mock.request_id, "manager03", "予算不足")

    mock_transition.assert_called_once_with(db, sr_mock.request_id, "Rejected", "予算不足")
    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["action"] == "REJECT"
    assert call_kwargs[1]["resource_type"] == "ServiceRequest"
    assert call_kwargs[1]["new_values"]["rejected_by"] == "manager03"
    assert call_kwargs[1]["new_values"]["comment"] == "予算不足"
    assert result is sr_mock


async def test_reject_request_default_comment():
    """reject_request: comment デフォルト値（空文字）"""
    from src.services.service_request_service import reject_request

    sr_mock = _make_sr_mock(status="Rejected")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ) as mock_transition, patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        await reject_request(db, sr_mock.request_id, "manager04")

    mock_transition.assert_called_once_with(db, sr_mock.request_id, "Rejected", "")
    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["new_values"]["comment"] == ""


async def test_reject_request_resource_id_matches_sr():
    """reject_request: resource_id が sr.request_id の文字列と一致する"""
    from src.services.service_request_service import reject_request

    rid = uuid.uuid4()
    sr_mock = _make_sr_mock(request_id=rid, status="Rejected")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ), patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ) as mock_audit:
        await reject_request(db, rid, "rejecter")

    call_kwargs = mock_audit.call_args
    assert call_kwargs[1]["resource_id"] == str(rid)


async def test_reject_request_returns_sr_object():
    """reject_request: ServiceRequest オブジェクトを返す"""
    from src.services.service_request_service import reject_request

    sr_mock = _make_sr_mock(status="Rejected")
    db = AsyncMock()

    with patch(
        "src.services.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr_mock),
    ), patch(
        "src.services.service_request_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ):
        result = await reject_request(db, sr_mock.request_id, "user")

    assert result is sr_mock
