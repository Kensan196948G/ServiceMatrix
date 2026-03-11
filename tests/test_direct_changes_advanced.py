"""changes.py 未カバーエンドポイントの直接呼び出しカバレッジテスト

対象: src/api/v1/changes.py
目的: カバレッジ 58% → 70%+ 達成
カバー対象:
  - get_change_calendar  (lines 110-167): 日付バリデーション + グループ化ループ
  - reschedule_change    (lines 236-251): 再スケジュール
  - submit_for_cab       (lines 364-377): CABレビュー申請
  - schedule_change      (lines 395-411): スケジュール設定
  - implement_change     (lines 428-441): 実装開始
  - complete_change      (lines 458-471): 実装完了
  - close_change         (lines 488-501): クローズ

Issue B5 対応
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.change import Change
from src.models.user import User, UserRole
from src.schemas.change import (
    CABApproval,
    ChangeStatusTransition,
    RescheduleRequest,
    ScheduleRequest,
)

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 3, 11, 10, 0, 0, tzinfo=UTC)


# ─── ヘルパー ──────────────────────────────────────────────────────────────


def _make_user():
    u = MagicMock(spec=User)
    u.user_id = uuid.uuid4()
    u.role = UserRole.SYSTEM_ADMIN
    return u


def _make_change_mock(
    *,
    status: str = "Approved",
    with_schedule: bool = True,
    with_end: bool = True,
):
    c = MagicMock(spec=Change)
    c.change_id = uuid.uuid4()
    c.change_number = "CHG-2026-000001"
    c.title = "Test Change"
    c.change_type = "Normal"
    c.status = status
    c.risk_level = "Medium"
    c.risk_score = 50
    c.scheduled_start_at = NOW if with_schedule else None
    c.scheduled_end_at = NOW if with_end else None
    c.created_at = NOW
    return c


def _make_db_with_change(change):
    """1件の変更を返すDBモック"""
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = change
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_db_not_found():
    """変更が見つからないDBモック"""
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    return db


# ─── get_change_calendar テスト (lines 110-167) ──────────────────────────


async def test_get_change_calendar_invalid_date():
    """get_change_calendar: 不正な日付形式 → 422 HTTPException (lines 120-124)"""
    from fastapi import HTTPException

    from src.api.v1.changes import get_change_calendar

    db = MagicMock()
    user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await get_change_calendar(
            start_date="2026/03/01",  # スラッシュ区切りは不正
            end_date="2026-03-31",
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 422
    assert "日付形式" in exc_info.value.detail


async def test_get_change_calendar_invalid_end_date():
    """get_change_calendar: 終了日が不正 → 422 HTTPException"""
    from fastapi import HTTPException

    from src.api.v1.changes import get_change_calendar

    db = MagicMock()
    user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await get_change_calendar(
            start_date="2026-03-01",
            end_date="not-a-date",
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 422


async def test_get_change_calendar_with_changes(monkeypatch):
    """get_change_calendar: 変更あり → 日付別グループ化 (lines 138-166)"""
    from src.api.v1.changes import get_change_calendar

    # scheduled_start_at あり
    c1 = _make_change_mock(status="Approved", with_schedule=True)
    c1.scheduled_start_at = datetime(2026, 3, 15, 9, 0, 0)
    c1.scheduled_end_at = datetime(2026, 3, 15, 12, 0, 0)

    # scheduled_start_at なし → created_at にフォールバック
    c2 = _make_change_mock(status="Scheduled", with_schedule=False)
    c2.scheduled_start_at = None
    c2.created_at = datetime(2026, 3, 16, 10, 0, 0)
    c2.scheduled_end_at = None

    # 同日の2件目 → 既存 date_key に追加
    c3 = _make_change_mock(status="Draft")
    c3.scheduled_start_at = datetime(2026, 3, 15, 14, 0, 0)
    c3.scheduled_end_at = None

    db = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [c1, c2, c3]
    result = MagicMock()
    result.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result)

    user = _make_user()

    response = await get_change_calendar(
        start_date="2026-03-01",
        end_date="2026-03-31",
        db=db,
        current_user=user,
    )

    assert response["start_date"] == "2026-03-01"
    assert response["end_date"] == "2026-03-31"
    assert response["total"] == 3
    assert len(response["events"]) == 2  # 2026-03-15 と 2026-03-16

    # 2026-03-15 には c1 + c3 の2件
    events_by_date = {e["date"]: e["changes"] for e in response["events"]}
    assert len(events_by_date["2026-03-15"]) == 2
    assert len(events_by_date["2026-03-16"]) == 1


async def test_get_change_calendar_empty():
    """get_change_calendar: 変更なし → events=[]"""
    from src.api.v1.changes import get_change_calendar

    db = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    result = MagicMock()
    result.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result)

    user = _make_user()

    response = await get_change_calendar(
        start_date="2026-03-01",
        end_date="2026-03-31",
        db=db,
        current_user=user,
    )

    assert response["total"] == 0
    assert response["events"] == []


# ─── reschedule_change テスト (lines 236-251) ──────────────────────────


async def test_reschedule_change_approved_success():
    """reschedule_change: Approved → スケジュール更新成功 (line 246-250)"""
    from src.api.v1.changes import reschedule_change

    change = _make_change_mock(status="Approved")
    db = _make_db_with_change(change)
    user = _make_user()

    new_start = datetime(2026, 4, 1, 9, 0, 0)
    new_end = datetime(2026, 4, 1, 18, 0, 0)
    data = RescheduleRequest(scheduled_start=new_start, scheduled_end=new_end)

    result = await reschedule_change(
        change_id=change.change_id,
        data=data,
        db=db,
        current_user=user,
    )

    assert change.scheduled_start_at == new_start
    assert change.scheduled_end_at == new_end
    db.flush.assert_called_once()
    db.refresh.assert_called_once()


async def test_reschedule_change_scheduled_success():
    """reschedule_change: Scheduled → 再スケジュール（終了日なし）"""
    from src.api.v1.changes import reschedule_change

    change = _make_change_mock(status="Scheduled")
    db = _make_db_with_change(change)
    user = _make_user()

    new_start = datetime(2026, 4, 2, 10, 0, 0)
    data = RescheduleRequest(scheduled_start=new_start, scheduled_end=None)

    await reschedule_change(
        change_id=change.change_id,
        data=data,
        db=db,
        current_user=user,
    )

    assert change.scheduled_start_at == new_start
    # scheduled_end は更新されない（data.scheduled_end is None）
    db.flush.assert_called_once()


async def test_reschedule_change_not_found():
    """reschedule_change: 変更なし → 404"""
    from fastapi import HTTPException

    from src.api.v1.changes import reschedule_change

    db = _make_db_not_found()
    user = _make_user()
    data = RescheduleRequest(scheduled_start=datetime(2026, 4, 1, 9, 0, 0))

    with pytest.raises(HTTPException) as exc_info:
        await reschedule_change(
            change_id=uuid.uuid4(),
            data=data,
            db=db,
            current_user=user,
        )
    assert exc_info.value.status_code == 404


async def test_reschedule_change_wrong_status():
    """reschedule_change: Approved/Scheduled 以外 → 422 (lines 241-245)"""
    from fastapi import HTTPException

    from src.api.v1.changes import reschedule_change

    change = _make_change_mock(status="Draft")
    db = _make_db_with_change(change)
    user = _make_user()
    data = RescheduleRequest(scheduled_start=datetime(2026, 4, 1, 9, 0, 0))

    with pytest.raises(HTTPException) as exc_info:
        await reschedule_change(
            change_id=change.change_id,
            data=data,
            db=db,
            current_user=user,
        )
    assert exc_info.value.status_code == 422
    assert "Approved" in exc_info.value.detail


# ─── submit_for_cab テスト (lines 364-377) ────────────────────────────


async def test_submit_for_cab_success():
    """submit_for_cab: 成功 → Draft → Submitted (lines 364-377)"""
    from src.api.v1.changes import submit_for_cab

    change = _make_change_mock(status="Draft")
    db = _make_db_with_change(change)
    user = _make_user()

    submitted_change = _make_change_mock(status="Submitted")

    with (
        patch(
            "src.api.v1.changes.change_service.transition_change_status",
            new=AsyncMock(return_value=submitted_change),
        ),
        patch(
            "src.api.v1.changes.ws_manager.broadcast",
            new=AsyncMock(),
        ),
    ):
        result = await submit_for_cab(
            change_id=change.change_id,
            db=db,
            current_user=user,
        )

    assert result.status == "Submitted"


async def test_submit_for_cab_not_found():
    """submit_for_cab: 変更なし → 404"""
    from fastapi import HTTPException

    from src.api.v1.changes import submit_for_cab

    db = _make_db_not_found()
    user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await submit_for_cab(change_id=uuid.uuid4(), db=db, current_user=user)
    assert exc_info.value.status_code == 404


async def test_submit_for_cab_value_error():
    """submit_for_cab: 遷移エラー → 422"""
    from fastapi import HTTPException

    from src.api.v1.changes import submit_for_cab

    change = _make_change_mock(status="Closed")
    db = _make_db_with_change(change)
    user = _make_user()

    with patch(
        "src.api.v1.changes.change_service.transition_change_status",
        new=AsyncMock(side_effect=ValueError("Invalid transition")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await submit_for_cab(change_id=change.change_id, db=db, current_user=user)
    assert exc_info.value.status_code == 422


# ─── schedule_change テスト (lines 395-411) ──────────────────────────


async def test_schedule_change_success_with_end():
    """schedule_change: end_at あり → Approved → Scheduled"""
    from src.api.v1.changes import schedule_change

    change = _make_change_mock(status="Approved")
    db = _make_db_with_change(change)
    user = _make_user()

    scheduled_change = _make_change_mock(status="Scheduled")
    data = ScheduleRequest(
        scheduled_start_at=datetime(2026, 4, 1, 9, 0, 0),
        scheduled_end_at=datetime(2026, 4, 1, 18, 0, 0),
    )

    with (
        patch(
            "src.api.v1.changes.change_service.transition_change_status",
            new=AsyncMock(return_value=scheduled_change),
        ),
        patch(
            "src.api.v1.changes.ws_manager.broadcast",
            new=AsyncMock(),
        ),
    ):
        result = await schedule_change(
            change_id=change.change_id,
            data=data,
            db=db,
            current_user=user,
        )

    assert result.status == "Scheduled"
    assert change.scheduled_start_at == data.scheduled_start_at
    assert change.scheduled_end_at == data.scheduled_end_at


async def test_schedule_change_success_without_end():
    """schedule_change: end_at なし → scheduled_end_at は変更しない (line 401 False branch)"""
    from src.api.v1.changes import schedule_change

    change = _make_change_mock(status="Approved")
    db = _make_db_with_change(change)
    user = _make_user()

    scheduled_change = _make_change_mock(status="Scheduled")
    data = ScheduleRequest(
        scheduled_start_at=datetime(2026, 4, 1, 9, 0, 0),
        scheduled_end_at=None,
    )

    with (
        patch(
            "src.api.v1.changes.change_service.transition_change_status",
            new=AsyncMock(return_value=scheduled_change),
        ),
        patch(
            "src.api.v1.changes.ws_manager.broadcast",
            new=AsyncMock(),
        ),
    ):
        result = await schedule_change(
            change_id=change.change_id,
            data=data,
            db=db,
            current_user=user,
        )

    assert result.status == "Scheduled"


async def test_schedule_change_not_found():
    """schedule_change: 変更なし → 404"""
    from fastapi import HTTPException

    from src.api.v1.changes import schedule_change

    db = _make_db_not_found()
    user = _make_user()
    data = ScheduleRequest(scheduled_start_at=datetime(2026, 4, 1, 9, 0, 0))

    with pytest.raises(HTTPException) as exc_info:
        await schedule_change(change_id=uuid.uuid4(), data=data, db=db, current_user=user)
    assert exc_info.value.status_code == 404


async def test_schedule_change_value_error():
    """schedule_change: 遷移エラー → 422"""
    from fastapi import HTTPException

    from src.api.v1.changes import schedule_change

    change = _make_change_mock(status="Draft")
    db = _make_db_with_change(change)
    user = _make_user()
    data = ScheduleRequest(scheduled_start_at=datetime(2026, 4, 1, 9, 0, 0))

    with patch(
        "src.api.v1.changes.change_service.transition_change_status",
        new=AsyncMock(side_effect=ValueError("Not approved yet")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await schedule_change(change_id=change.change_id, data=data, db=db, current_user=user)
    assert exc_info.value.status_code == 422


# ─── implement_change テスト (lines 428-441) ──────────────────────────


async def test_implement_change_success():
    """implement_change: Scheduled → In_Progress"""
    from src.api.v1.changes import implement_change

    change = _make_change_mock(status="Scheduled")
    db = _make_db_with_change(change)
    user = _make_user()

    in_progress_change = _make_change_mock(status="In_Progress")

    with (
        patch(
            "src.api.v1.changes.change_service.transition_change_status",
            new=AsyncMock(return_value=in_progress_change),
        ),
        patch(
            "src.api.v1.changes.ws_manager.broadcast",
            new=AsyncMock(),
        ),
    ):
        result = await implement_change(
            change_id=change.change_id, db=db, current_user=user
        )

    assert result.status == "In_Progress"


async def test_implement_change_not_found():
    """implement_change: 変更なし → 404"""
    from fastapi import HTTPException

    from src.api.v1.changes import implement_change

    db = _make_db_not_found()
    user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await implement_change(change_id=uuid.uuid4(), db=db, current_user=user)
    assert exc_info.value.status_code == 404


async def test_implement_change_value_error():
    """implement_change: 遷移エラー → 422"""
    from fastapi import HTTPException

    from src.api.v1.changes import implement_change

    change = _make_change_mock(status="Draft")
    db = _make_db_with_change(change)
    user = _make_user()

    with patch(
        "src.api.v1.changes.change_service.transition_change_status",
        new=AsyncMock(side_effect=ValueError("Cannot implement")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await implement_change(change_id=change.change_id, db=db, current_user=user)
    assert exc_info.value.status_code == 422


# ─── complete_change テスト (lines 458-471) ──────────────────────────


async def test_complete_change_success():
    """complete_change: In_Progress → Completed"""
    from src.api.v1.changes import complete_change

    change = _make_change_mock(status="In_Progress")
    db = _make_db_with_change(change)
    user = _make_user()

    completed_change = _make_change_mock(status="Completed")

    with (
        patch(
            "src.api.v1.changes.change_service.transition_change_status",
            new=AsyncMock(return_value=completed_change),
        ),
        patch(
            "src.api.v1.changes.ws_manager.broadcast",
            new=AsyncMock(),
        ),
    ):
        result = await complete_change(
            change_id=change.change_id, db=db, current_user=user
        )

    assert result.status == "Completed"


async def test_complete_change_not_found():
    """complete_change: 変更なし → 404"""
    from fastapi import HTTPException

    from src.api.v1.changes import complete_change

    db = _make_db_not_found()
    user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await complete_change(change_id=uuid.uuid4(), db=db, current_user=user)
    assert exc_info.value.status_code == 404


async def test_complete_change_value_error():
    """complete_change: 遷移エラー → 422"""
    from fastapi import HTTPException

    from src.api.v1.changes import complete_change

    change = _make_change_mock(status="Draft")
    db = _make_db_with_change(change)
    user = _make_user()

    with patch(
        "src.api.v1.changes.change_service.transition_change_status",
        new=AsyncMock(side_effect=ValueError("Cannot complete")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await complete_change(change_id=change.change_id, db=db, current_user=user)
    assert exc_info.value.status_code == 422


# ─── close_change テスト (lines 488-501) ──────────────────────────────


async def test_close_change_success():
    """close_change: Completed → Closed"""
    from src.api.v1.changes import close_change

    change = _make_change_mock(status="Completed")
    db = _make_db_with_change(change)
    user = _make_user()

    closed_change = _make_change_mock(status="Closed")

    with (
        patch(
            "src.api.v1.changes.change_service.transition_change_status",
            new=AsyncMock(return_value=closed_change),
        ),
        patch(
            "src.api.v1.changes.ws_manager.broadcast",
            new=AsyncMock(),
        ),
    ):
        result = await close_change(
            change_id=change.change_id, db=db, current_user=user
        )

    assert result.status == "Closed"


async def test_close_change_not_found():
    """close_change: 変更なし → 404"""
    from fastapi import HTTPException

    from src.api.v1.changes import close_change

    db = _make_db_not_found()
    user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await close_change(change_id=uuid.uuid4(), db=db, current_user=user)
    assert exc_info.value.status_code == 404


async def test_close_change_value_error():
    """close_change: 遷移エラー → 422"""
    from fastapi import HTTPException

    from src.api.v1.changes import close_change

    change = _make_change_mock(status="In_Progress")
    db = _make_db_with_change(change)
    user = _make_user()

    with patch(
        "src.api.v1.changes.change_service.transition_change_status",
        new=AsyncMock(side_effect=ValueError("Cannot close")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await close_change(change_id=change.change_id, db=db, current_user=user)
    assert exc_info.value.status_code == 422
