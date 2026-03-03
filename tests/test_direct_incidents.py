"""incidents.py エンドポイント関数の直接呼び出しユニットテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.incidents import (
    create_incident,
    get_incident,
    list_incidents,
    transition_incident_status,
    update_incident,
)
from src.models.incident import Incident
from src.models.user import User, UserRole
from src.schemas.incident import (
    IncidentCreate,
    IncidentStatusTransition,
    IncidentUpdate,
)

pytestmark = pytest.mark.asyncio

NOW = datetime.now(UTC)


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


def _make_incident(**overrides):
    defaults = {
        "incident_id": uuid.uuid4(),
        "incident_number": "INC-2024-000001",
        "title": "テストインシデント",
        "description": None,
        "priority": "P3",
        "status": "New",
        "assigned_to": None,
        "assigned_team_id": None,
        "reported_by": None,
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "sla_response_due_at": None,
        "sla_resolution_due_at": None,
        "sla_breached": False,
        "category": None,
        "subcategory": None,
        "affected_service": None,
        "resolution_notes": None,
        "ai_triage_notes": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    incident = MagicMock(spec=Incident)
    for k, v in defaults.items():
        setattr(incident, k, v)
    return incident


def _mock_db_returning(items):
    """DBモック: execute -> scalars().all() / scalar_one_or_none"""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = items
    result_mock.scalar_one_or_none.return_value = items[0] if items else None
    result_mock.scalar_one.return_value = len(items)
    db.execute.return_value = result_mock
    return db


def _mock_db_with_count_and_items(count, items):
    """DBモック: 最初のexecuteでcount、2番目でitems"""
    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = count

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = items

    db.execute.side_effect = [count_result, items_result]
    return db


# --- list_incidents() テスト --------------------------------------------------


async def test_list_incidents_empty_direct():
    """list_incidents() 直接呼び出し: 空リスト"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter=None, priority=None
    )

    assert result.total == 0
    assert result.items == []
    assert result.page == 1
    assert result.size == 20


async def test_list_incidents_with_data_direct():
    """list_incidents() 直接呼び出し: データあり"""
    user = _make_user()
    incident = _make_incident()
    db = _mock_db_with_count_and_items(1, [incident])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter=None, priority=None
    )

    assert result.total == 1
    assert len(result.items) == 1


async def test_list_incidents_with_status_filter_direct():
    """list_incidents() 直接呼び出し: statusフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter="New", priority=None
    )

    assert result.total == 0


async def test_list_incidents_with_priority_filter_direct():
    """list_incidents() 直接呼び出し: priorityフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter=None, priority="P1"
    )

    assert result.total == 0


async def test_list_incidents_pagination_direct():
    """list_incidents() 直接呼び出し: ページネーション"""
    user = _make_user()
    db = _mock_db_with_count_and_items(50, [])

    result = await list_incidents(
        db=db, current_user=user, page=3, size=10, status_filter=None, priority=None
    )

    assert result.total == 50
    assert result.page == 3
    assert result.size == 10
    assert result.pages == 5


# --- create_incident() テスト -------------------------------------------------


async def test_create_incident_direct():
    """create_incident() 直接呼び出し: 正常作成"""
    user = _make_user()
    incident = _make_incident()
    db = AsyncMock()
    background_tasks = MagicMock()

    data = IncidentCreate(title="テストインシデント", priority="P3")

    with patch(
        "src.api.v1.incidents.incident_service.create_incident",
        new=AsyncMock(return_value=incident),
    ):
        result = await create_incident(
            data=data, background_tasks=background_tasks, db=db, current_user=user
        )

    assert result.incident_number == "INC-2024-000001"
    background_tasks.add_task.assert_called_once()


# --- get_incident() テスト ----------------------------------------------------


async def test_get_incident_found_direct():
    """get_incident() 直接呼び出し: インシデントが見つかる"""
    user = _make_user()
    incident = _make_incident()
    db = _mock_db_returning([incident])

    result = await get_incident(incident_id=incident.incident_id, db=db, current_user=user)

    assert result == incident


async def test_get_incident_not_found_direct():
    """get_incident() 直接呼び出し: インシデントが見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    with pytest.raises(HTTPException) as exc_info:
        await get_incident(incident_id=uuid.uuid4(), db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- update_incident() テスト -------------------------------------------------


async def test_update_incident_success_direct():
    """update_incident() 直接呼び出し: 正常更新"""
    user = _make_user()
    incident = _make_incident()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    data = IncidentUpdate(description="更新された説明")
    result = await update_incident(
        incident_id=incident.incident_id, data=data, db=db, current_user=user
    )

    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once()


async def test_update_incident_not_found_direct():
    """update_incident() 直接呼び出し: インシデントが見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    data = IncidentUpdate(description="更新")
    with pytest.raises(HTTPException) as exc_info:
        await update_incident(incident_id=uuid.uuid4(), data=data, db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- transition_incident_status() テスト --------------------------------------


async def test_transition_incident_success_direct():
    """transition_incident_status() 直接呼び出し: 正常遷移"""
    user = _make_user()
    incident = _make_incident(status="New")
    transitioned = _make_incident(status="Acknowledged")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    transition = IncidentStatusTransition(new_status="Acknowledged")

    with patch(
        "src.api.v1.incidents.incident_service.transition_status",
        new=AsyncMock(return_value=transitioned),
    ):
        result = await transition_incident_status(
            incident_id=incident.incident_id,
            transition=transition,
            db=db,
            current_user=user,
        )

    assert result.status == "Acknowledged"


async def test_transition_incident_not_found_direct():
    """transition_incident_status() 直接呼び出し: インシデントが見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    transition = IncidentStatusTransition(new_status="Acknowledged")

    with pytest.raises(HTTPException) as exc_info:
        await transition_incident_status(
            incident_id=uuid.uuid4(),
            transition=transition,
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 404


async def test_transition_incident_invalid_direct():
    """transition_incident_status() 直接呼び出し: 不正遷移 -> 422"""
    from fastapi import HTTPException

    user = _make_user()
    incident = _make_incident(status="New")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    transition = IncidentStatusTransition(new_status="Closed")

    with (
        patch(
            "src.api.v1.incidents.incident_service.transition_status",
            new=AsyncMock(side_effect=ValueError("無効な遷移")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await transition_incident_status(
            incident_id=incident.incident_id,
            transition=transition,
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 422
