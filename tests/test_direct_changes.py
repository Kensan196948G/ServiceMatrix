"""changes.py エンドポイント関数の直接呼び出しユニットテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.changes import (
    assess_change_risk,
    cab_approval,
    create_change,
    get_change,
    list_changes,
    transition_change_status,
    update_change,
)
from src.models.change import Change
from src.models.user import User, UserRole
from src.schemas.change import (
    CABApproval,
    ChangeCreate,
    ChangeStatusTransition,
    ChangeUpdate,
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


def _make_change(**overrides):
    defaults = {
        "change_id": uuid.uuid4(),
        "change_number": "CHG-2024-000001",
        "title": "テスト変更",
        "description": None,
        "change_type": "Normal",
        "status": "Draft",
        "risk_score": 30,
        "risk_level": "Low",
        "impact_level": "Medium",
        "urgency_level": "Low",
        "requested_by": None,
        "assigned_to": None,
        "cab_approved_by": None,
        "scheduled_start_at": None,
        "scheduled_end_at": None,
        "actual_start_at": None,
        "actual_end_at": None,
        "cab_reviewed_at": None,
        "implementation_plan": None,
        "rollback_plan": None,
        "test_plan": None,
        "cab_notes": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    change = MagicMock(spec=Change)
    for k, v in defaults.items():
        setattr(change, k, v)
    return change


def _mock_db_returning(items):
    """DBモック: execute → scalars().all() → items"""
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


# ─── list_changes() テスト ─────────────────────────────────────────────────────


async def test_list_changes_direct():
    """list_changes() 直接呼び出し: 空リスト"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_changes(db=db, current_user=user, page=1, size=20, status_filter=None)

    assert result.total == 0
    assert result.items == []
    assert result.page == 1
    assert result.size == 20


async def test_list_changes_with_data_direct():
    """list_changes() 直接呼び出し: データあり"""
    user = _make_user()
    change = _make_change()
    db = _mock_db_with_count_and_items(1, [change])

    result = await list_changes(db=db, current_user=user, page=1, size=20, status_filter=None)

    assert result.total == 1
    assert len(result.items) == 1


async def test_list_changes_with_status_filter_direct():
    """list_changes() 直接呼び出し: statusフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_changes(db=db, current_user=user, page=1, size=20, status_filter="Draft")

    assert result.total == 0


async def test_list_changes_pagination_direct():
    """list_changes() 直接呼び出し: ページネーション"""
    user = _make_user()
    db = _mock_db_with_count_and_items(50, [])

    result = await list_changes(db=db, current_user=user, page=2, size=10, status_filter=None)

    assert result.total == 50
    assert result.page == 2
    assert result.size == 10
    assert result.pages == 5


# ─── create_change() テスト ────────────────────────────────────────────────────


async def test_create_change_direct():
    """create_change() 直接呼び出し: 正常作成"""
    user = _make_user()
    change = _make_change()
    db = AsyncMock()

    data = ChangeCreate(title="テスト変更", change_type="Normal")

    with patch(
        "src.api.v1.changes.change_service.create_change",
        new=AsyncMock(return_value=change),
    ):
        result = await create_change(data=data, db=db, current_user=user)

    assert result.change_number == "CHG-2024-000001"


# ─── get_change() テスト ───────────────────────────────────────────────────────


async def test_get_change_found_direct():
    """get_change() 直接呼び出し: 変更が見つかる"""
    user = _make_user()
    change = _make_change()
    db = _mock_db_returning([change])

    result = await get_change(change_id=change.change_id, db=db, current_user=user)

    assert result == change


async def test_get_change_not_found_direct():
    """get_change() 直接呼び出し: 変更が見つからない → 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    with pytest.raises(HTTPException) as exc_info:
        await get_change(change_id=uuid.uuid4(), db=db, current_user=user)

    assert exc_info.value.status_code == 404


# ─── update_change() テスト ────────────────────────────────────────────────────


async def test_update_change_success_direct():
    """update_change() 直接呼び出し: 正常更新"""
    user = _make_user()
    change = _make_change()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = change
    db.execute.return_value = result_mock

    data = ChangeUpdate(description="更新された説明")
    result = await update_change(change_id=change.change_id, data=data, db=db, current_user=user)

    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once()


async def test_update_change_not_found_direct():
    """update_change() 直接呼び出し: 変更が見つからない → 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    data = ChangeUpdate(description="更新")
    with pytest.raises(HTTPException) as exc_info:
        await update_change(change_id=uuid.uuid4(), data=data, db=db, current_user=user)

    assert exc_info.value.status_code == 404


# ─── transition_change_status() テスト ──────────────────────────────────────────


async def test_transition_success_direct():
    """transition_change_status() 直接呼び出し: 正常遷移"""
    user = _make_user()
    change = _make_change(status="Draft")
    transitioned_change = _make_change(status="Submitted")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = change
    db.execute.return_value = result_mock

    transition = ChangeStatusTransition(new_status="Submitted")

    with patch(
        "src.api.v1.changes.change_service.transition_change_status",
        new=AsyncMock(return_value=transitioned_change),
    ):
        result = await transition_change_status(
            change_id=change.change_id, transition=transition, db=db, current_user=user
        )

    assert result.status == "Submitted"


async def test_transition_not_found_direct():
    """transition_change_status() 直接呼び出し: 変更が見つからない → 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    transition = ChangeStatusTransition(new_status="Submitted")

    with pytest.raises(HTTPException) as exc_info:
        await transition_change_status(
            change_id=uuid.uuid4(), transition=transition, db=db, current_user=user
        )

    assert exc_info.value.status_code == 404


async def test_transition_invalid_direct():
    """transition_change_status() 直接呼び出し: 不正遷移 → 422"""
    from fastapi import HTTPException

    user = _make_user()
    change = _make_change(status="Draft")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = change
    db.execute.return_value = result_mock

    transition = ChangeStatusTransition(new_status="Approved")

    with (
        patch(
            "src.api.v1.changes.change_service.transition_change_status",
            new=AsyncMock(side_effect=ValueError("無効な遷移")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await transition_change_status(
            change_id=change.change_id, transition=transition, db=db, current_user=user
        )

    assert exc_info.value.status_code == 422


# ─── cab_approval() テスト ─────────────────────────────────────────────────────


async def test_cab_approval_success_direct():
    """cab_approval() 直接呼び出し: CAB承認成功"""
    user = _make_user()
    change = _make_change(status="CAB_Review")
    approved_change = _make_change(status="Approved")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = change
    db.execute.return_value = result_mock

    approval = CABApproval(approved=True, notes="問題なし")

    with patch(
        "src.api.v1.changes.change_service.approve_by_cab",
        new=AsyncMock(return_value=approved_change),
    ):
        result = await cab_approval(
            change_id=change.change_id, approval=approval, db=db, current_user=user
        )

    assert result.status == "Approved"


async def test_cab_approval_not_found_direct():
    """cab_approval() 直接呼び出し: 変更が見つからない → 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    approval = CABApproval(approved=True)

    with pytest.raises(HTTPException) as exc_info:
        await cab_approval(change_id=uuid.uuid4(), approval=approval, db=db, current_user=user)

    assert exc_info.value.status_code == 404


async def test_cab_approval_invalid_direct():
    """cab_approval() 直接呼び出し: 不正状態 → 422"""
    from fastapi import HTTPException

    user = _make_user()
    change = _make_change(status="Draft")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = change
    db.execute.return_value = result_mock

    approval = CABApproval(approved=True)

    with (
        patch(
            "src.api.v1.changes.change_service.approve_by_cab",
            new=AsyncMock(side_effect=ValueError("CAB_Review状態ではありません")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await cab_approval(change_id=change.change_id, approval=approval, db=db, current_user=user)

    assert exc_info.value.status_code == 422


# ─── assess_change_risk() テスト ───────────────────────────────────────────────


async def test_assess_risk_success_direct():
    """assess_change_risk() 直接呼び出し: リスク評価成功"""
    from src.services.change_risk_service import RiskAssessmentResult

    user = _make_user()
    db = AsyncMock()
    change_id = uuid.uuid4()

    mock_result = RiskAssessmentResult(
        change_id=str(change_id),
        total_score=50,
        risk_level="Medium",
        factors=[],
        recommendations=["テスト推奨事項"],
        maintenance_window_required=False,
    )

    with patch(
        "src.api.v1.changes.change_risk_service.assess_risk",
        new=AsyncMock(return_value=mock_result),
    ):
        result = await assess_change_risk(change_id=change_id, db=db, current_user=user)

    assert result.total_score == 50
    assert result.risk_level == "Medium"


async def test_assess_risk_not_found_direct():
    """assess_change_risk() 直接呼び出し: 変更なし → 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = AsyncMock()

    with (
        patch(
            "src.api.v1.changes.change_risk_service.assess_risk",
            new=AsyncMock(side_effect=ValueError("変更が見つかりません")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await assess_change_risk(change_id=uuid.uuid4(), db=db, current_user=user)

    assert exc_info.value.status_code == 404
