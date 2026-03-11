"""service_requests.py エンドポイント直接呼び出しテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.v1.service_requests import (
    approve_service_request,
    complete_service_request,
    create_incident_from_sr,
    create_service_request,
    get_service_request,
    list_service_requests,
    reject_service_request,
    start_service_request_fulfillment,
    submit_service_request,
    transition_service_request_status,
    update_service_request,
)
from src.models.user import User, UserRole
from src.schemas.service_request import (
    ServiceRequestApprovalAction,
    ServiceRequestCompleteAction,
    ServiceRequestCreate,
    ServiceRequestStatusTransition,
    ServiceRequestUpdate,
    ServiceRequestToIncidentRequest,
)

pytestmark = pytest.mark.asyncio

NOW = datetime.now(timezone.utc)


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_user(**overrides):
    defaults = {
        "user_id": uuid.uuid4(),
        "username": "testadmin",
        "email": "admin@test.com",
        "role": UserRole.SYSTEM_ADMIN,
        "is_active": True,
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_sr(**overrides):
    defaults = {
        "request_id": uuid.uuid4(),
        "request_number": "SR-2024-000001",
        "title": "テストSR",
        "description": None,
        "status": "New",
        "request_type": None,
        "requested_by": None,
        "assigned_to": None,
        "approved_by": None,
        "due_date": None,
        "fulfilled_at": None,
        "catalog_id": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    sr = MagicMock()
    for k, v in defaults.items():
        setattr(sr, k, v)
    return sr


def _make_incident_mock(**overrides):
    defaults = {
        "incident_id": uuid.uuid4(),
        "incident_number": "INC-2024-000001",
        "title": "[SR] テストSR",
    }
    defaults.update(overrides)
    inc = MagicMock()
    for k, v in defaults.items():
        setattr(inc, k, v)
    return inc


def _mock_db_with_sr(sr):
    """scalar_one_or_none() が sr を返すDB"""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sr
    db.execute.return_value = result
    return db


def _mock_db_empty():
    """scalar_one_or_none() が None を返すDB"""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    return db


# ─── list_service_requests ────────────────────────────────────────────────────


async def test_list_sr_direct():
    """list_service_requests() 直接呼び出し → PaginatedResponse を返す"""
    sr = _make_sr()
    user = _make_user()
    db = AsyncMock()

    with patch(
        "src.api.v1.service_requests.service_request_service.get_service_requests",
        new=AsyncMock(return_value=([sr], 1)),
    ):
        result = await list_service_requests(
            db=db, current_user=user, status_filter=None, skip=0, limit=20
        )

    assert result.total == 1
    assert result.size == 20


# ─── create_service_request ───────────────────────────────────────────────────


async def test_create_sr_direct():
    """create_service_request() 直接呼び出し → SR オブジェクトを返す"""
    sr = _make_sr()
    user = _make_user()
    db = AsyncMock()
    data = ServiceRequestCreate(title="新しいSR")

    with patch(
        "src.api.v1.service_requests.service_request_service.create_service_request",
        new=AsyncMock(return_value=sr),
    ):
        result = await create_service_request(data=data, db=db, current_user=user)

    assert result.request_number == "SR-2024-000001"


# ─── get_service_request ──────────────────────────────────────────────────────


async def test_get_sr_found_direct():
    """get_service_request() 直接呼び出し: SR が存在する → 返す"""
    sr = _make_sr()
    user = _make_user()

    with patch(
        "src.api.v1.service_requests.service_request_service.get_service_request",
        new=AsyncMock(return_value=sr),
    ):
        result = await get_service_request(
            request_id=sr.request_id, db=AsyncMock(), current_user=user
        )

    assert result == sr


async def test_get_sr_not_found_direct():
    """get_service_request() 直接呼び出し: SR が存在しない → 404"""
    user = _make_user()

    with patch(
        "src.api.v1.service_requests.service_request_service.get_service_request",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_service_request(
                request_id=uuid.uuid4(), db=AsyncMock(), current_user=user
            )

    assert exc_info.value.status_code == 404


# ─── update_service_request ───────────────────────────────────────────────────


async def test_update_sr_success_direct():
    """update_service_request() 直接呼び出し: 正常更新 → SR を返す"""
    sr = _make_sr(description="更新済み")
    user = _make_user()
    data = ServiceRequestUpdate(description="更新済み")

    with patch(
        "src.api.v1.service_requests.service_request_service.update_service_request",
        new=AsyncMock(return_value=sr),
    ):
        result = await update_service_request(
            request_id=sr.request_id, data=data, db=AsyncMock(), current_user=user
        )

    assert result.description == "更新済み"


async def test_update_sr_not_found_direct():
    """update_service_request() 直接呼び出し: SR なし → 404"""
    user = _make_user()
    data = ServiceRequestUpdate(description="更新")

    with patch(
        "src.api.v1.service_requests.service_request_service.update_service_request",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await update_service_request(
                request_id=uuid.uuid4(), data=data, db=AsyncMock(), current_user=user
            )

    assert exc_info.value.status_code == 404


# ─── transition_service_request_status ───────────────────────────────────────


async def test_transition_sr_success_direct():
    """transition() 直接呼び出し: 正常遷移"""
    sr = _make_sr(status="Pending_Approval")
    user = _make_user()
    transition = ServiceRequestStatusTransition(target_status="Pending_Approval")

    with patch(
        "src.api.v1.service_requests.service_request_service.transition_service_request_status",
        new=AsyncMock(return_value=sr),
    ):
        result = await transition_service_request_status(
            request_id=sr.request_id,
            transition=transition,
            db=AsyncMock(),
            current_user=user,
        )

    assert result.status == "Pending_Approval"


async def test_transition_sr_valueerror_direct():
    """transition() 直接呼び出し: 不正遷移 → 422"""
    user = _make_user()
    transition = ServiceRequestStatusTransition(target_status="Fulfilled")

    with patch(
        "src.api.v1.service_requests.service_request_service.transition_service_request_status",
        new=AsyncMock(side_effect=ValueError("不正なステータス遷移")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await transition_service_request_status(
                request_id=uuid.uuid4(),
                transition=transition,
                db=AsyncMock(),
                current_user=user,
            )

    assert exc_info.value.status_code == 422


# ─── submit_service_request ───────────────────────────────────────────────────


async def test_submit_sr_success_direct():
    """submit_service_request() 直接呼び出し: 正常提出"""
    sr = _make_sr(status="Pending_Approval")
    user = _make_user()

    with patch(
        "src.api.v1.service_requests.service_request_service.submit_request",
        new=AsyncMock(return_value=sr),
    ):
        result = await submit_service_request(
            request_id=sr.request_id, db=AsyncMock(), current_user=user
        )

    assert result.status == "Pending_Approval"


async def test_submit_sr_valueerror_direct():
    """submit_service_request() 直接呼び出し: ValueError → 422"""
    user = _make_user()

    with patch(
        "src.api.v1.service_requests.service_request_service.submit_request",
        new=AsyncMock(side_effect=ValueError("提出できない状態")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await submit_service_request(
                request_id=uuid.uuid4(), db=AsyncMock(), current_user=user
            )

    assert exc_info.value.status_code == 422


# ─── approve_service_request ──────────────────────────────────────────────────


async def test_approve_sr_success_direct():
    """approve_service_request() 直接呼び出し: 正常承認"""
    sr = _make_sr(status="Approved")
    user = _make_user()
    action = ServiceRequestApprovalAction(actor="admin", comment="承認します")

    with patch(
        "src.api.v1.service_requests.service_request_service.approve_request",
        new=AsyncMock(return_value=sr),
    ):
        result = await approve_service_request(
            request_id=sr.request_id, action=action, db=AsyncMock(), current_user=user
        )

    assert result.status == "Approved"


async def test_approve_sr_valueerror_direct():
    """approve_service_request() 直接呼び出し: ValueError → 422"""
    user = _make_user()
    action = ServiceRequestApprovalAction(actor="admin")

    with patch(
        "src.api.v1.service_requests.service_request_service.approve_request",
        new=AsyncMock(side_effect=ValueError("承認できない状態")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await approve_service_request(
                request_id=uuid.uuid4(), action=action, db=AsyncMock(), current_user=user
            )

    assert exc_info.value.status_code == 422


# ─── reject_service_request ───────────────────────────────────────────────────


async def test_reject_sr_success_direct():
    """reject_service_request() 直接呼び出し: 正常却下"""
    sr = _make_sr(status="Rejected")
    user = _make_user()
    action = ServiceRequestApprovalAction(actor="admin", comment="却下")

    with patch(
        "src.api.v1.service_requests.service_request_service.reject_request",
        new=AsyncMock(return_value=sr),
    ):
        result = await reject_service_request(
            request_id=sr.request_id, action=action, db=AsyncMock(), current_user=user
        )

    assert result.status == "Rejected"


async def test_reject_sr_valueerror_direct():
    """reject_service_request() 直接呼び出し: ValueError → 422"""
    user = _make_user()
    action = ServiceRequestApprovalAction(actor="admin")

    with patch(
        "src.api.v1.service_requests.service_request_service.reject_request",
        new=AsyncMock(side_effect=ValueError("却下できない状態")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await reject_service_request(
                request_id=uuid.uuid4(), action=action, db=AsyncMock(), current_user=user
            )

    assert exc_info.value.status_code == 422


# ─── start_service_request_fulfillment ───────────────────────────────────────


async def test_start_sr_success_direct():
    """start_service_request_fulfillment() 直接呼び出し: 正常実行開始"""
    sr = _make_sr(status="In_Fulfillment")
    user = _make_user()

    with patch(
        "src.api.v1.service_requests.service_request_service.start_fulfillment",
        new=AsyncMock(return_value=sr),
    ):
        result = await start_service_request_fulfillment(
            request_id=sr.request_id, db=AsyncMock(), current_user=user
        )

    assert result.status == "In_Fulfillment"


async def test_start_sr_valueerror_direct():
    """start_service_request_fulfillment() 直接呼び出し: ValueError → 422"""
    user = _make_user()

    with patch(
        "src.api.v1.service_requests.service_request_service.start_fulfillment",
        new=AsyncMock(side_effect=ValueError("開始できない状態")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await start_service_request_fulfillment(
                request_id=uuid.uuid4(), db=AsyncMock(), current_user=user
            )

    assert exc_info.value.status_code == 422


# ─── complete_service_request ─────────────────────────────────────────────────


async def test_complete_sr_success_direct():
    """complete_service_request() 直接呼び出し: 正常完了"""
    sr = _make_sr(status="Fulfilled")
    user = _make_user()
    action = ServiceRequestCompleteAction(success=True)

    with patch(
        "src.api.v1.service_requests.service_request_service.complete_request",
        new=AsyncMock(return_value=sr),
    ):
        result = await complete_service_request(
            request_id=sr.request_id, action=action, db=AsyncMock(), current_user=user
        )

    assert result.status == "Fulfilled"


async def test_complete_sr_valueerror_direct():
    """complete_service_request() 直接呼び出し: ValueError → 422"""
    user = _make_user()
    action = ServiceRequestCompleteAction(success=False)

    with patch(
        "src.api.v1.service_requests.service_request_service.complete_request",
        new=AsyncMock(side_effect=ValueError("完了できない状態")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await complete_service_request(
                request_id=uuid.uuid4(), action=action, db=AsyncMock(), current_user=user
            )

    assert exc_info.value.status_code == 422


# ─── create_incident_from_sr ──────────────────────────────────────────────────


async def test_create_incident_from_sr_found_direct():
    """create_incident_from_sr() 直接呼び出し: SR存在 → インシデント作成"""
    sr_id = uuid.uuid4()
    sr = _make_sr(
        request_id=sr_id,
        request_number="SR-2024-000001",
        title="インシデント変換テスト",
        description="詳細説明",
        request_type="Software",
        requested_by=None,
    )
    incident = _make_incident_mock()
    user = _make_user()
    body = ServiceRequestToIncidentRequest(priority="P2")

    db = _mock_db_with_sr(sr)

    with patch(
        "src.api.v1.service_requests.incident_service.create_incident",
        new=AsyncMock(return_value=incident),
    ):
        result = await create_incident_from_sr(
            request_id=sr_id, body=body, db=db, current_user=user
        )

    assert result.incident_number == "INC-2024-000001"
    assert result.service_request_number == "SR-2024-000001"


async def test_create_incident_from_sr_with_notes_direct():
    """create_incident_from_sr() 直接呼び出し: additional_notes付き"""
    sr_id = uuid.uuid4()
    sr = _make_sr(
        request_id=sr_id,
        request_number="SR-2024-000002",
        title="追記付きSR",
        description=None,
        request_type=None,
        requested_by=None,
    )
    incident = _make_incident_mock(
        incident_id=uuid.uuid4(),
        incident_number="INC-2024-000002",
    )
    user = _make_user()
    body = ServiceRequestToIncidentRequest(
        priority="P1", additional_notes="緊急対応必要"
    )

    db = _mock_db_with_sr(sr)

    with patch(
        "src.api.v1.service_requests.incident_service.create_incident",
        new=AsyncMock(return_value=incident),
    ):
        result = await create_incident_from_sr(
            request_id=sr_id, body=body, db=db, current_user=user
        )

    assert "INC-" in result.incident_number


async def test_create_incident_from_sr_not_found_direct():
    """create_incident_from_sr() 直接呼び出し: SR なし → 404"""
    user = _make_user()
    body = ServiceRequestToIncidentRequest(priority="P3")
    db = _mock_db_empty()

    with pytest.raises(HTTPException) as exc_info:
        await create_incident_from_sr(
            request_id=uuid.uuid4(), body=body, db=db, current_user=user
        )

    assert exc_info.value.status_code == 404
