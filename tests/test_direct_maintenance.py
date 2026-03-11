"""maintenance.py エンドポイント直接呼び出しテスト - カバレッジ向上

対象: src/api/v1/maintenance.py
カバー対象行: 33, 50, 67-68, 93-94, 107-113, 127-137, 150-156
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_window(window_id=None, name="テストウィンドウ", is_active=True):
    w = MagicMock()
    w.window_id = window_id or uuid.uuid4()
    w.name = name
    w.description = None
    w.start_time = datetime.now(UTC) - timedelta(hours=1)
    w.end_time = datetime.now(UTC) + timedelta(hours=1)
    w.is_recurring = False
    w.recurrence_rule = None
    w.is_active = is_active
    w.created_by = uuid.uuid4()
    w.created_at = datetime.now(UTC)
    return w


def _make_scalars_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _make_scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_user():
    user = MagicMock()
    user.user_id = uuid.uuid4()
    return user


# ─── list_maintenance_windows (line 33) ───────────────────────────────────────


async def test_list_maintenance_windows_returns_all():
    """list_maintenance_windows: 全ウィンドウ一覧を返す（line 33）"""
    from src.api.v1.maintenance import list_maintenance_windows

    w1 = _make_window(name="ウィンドウ1")
    w2 = _make_window(name="ウィンドウ2")
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars_result([w1, w2]))
    current_user = _make_user()

    result = await list_maintenance_windows(db=db, current_user=current_user)

    assert len(result) == 2
    assert result[0].name == "ウィンドウ1"


async def test_list_maintenance_windows_empty():
    """list_maintenance_windows: ウィンドウなし → 空リスト"""
    from src.api.v1.maintenance import list_maintenance_windows

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars_result([]))
    current_user = _make_user()

    result = await list_maintenance_windows(db=db, current_user=current_user)

    assert result == []


# ─── list_active_windows (line 50) ────────────────────────────────────────────


async def test_list_active_windows_returns_active():
    """list_active_windows: アクティブウィンドウを返す（line 50）"""
    from src.api.v1.maintenance import list_active_windows

    w = _make_window(is_active=True)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars_result([w]))
    current_user = _make_user()

    result = await list_active_windows(db=db, current_user=current_user)

    assert len(result) == 1
    assert result[0].is_active is True


async def test_list_active_windows_empty():
    """list_active_windows: アクティブなし → 空リスト"""
    from src.api.v1.maintenance import list_active_windows

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars_result([]))
    current_user = _make_user()

    result = await list_active_windows(db=db, current_user=current_user)

    assert result == []


# ─── check_maintenance (lines 67-68) ──────────────────────────────────────────


async def test_check_maintenance_in_maintenance():
    """check_maintenance: メンテナンス中 → in_maintenance=True（lines 67-68）"""
    from src.api.v1.maintenance import check_maintenance

    w = _make_window(is_active=True)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars_result([w]))
    current_user = _make_user()

    result = await check_maintenance(db=db, current_user=current_user)

    assert result["in_maintenance"] is True
    assert len(result["windows"]) == 1


async def test_check_maintenance_not_in_maintenance():
    """check_maintenance: メンテナンスなし → in_maintenance=False"""
    from src.api.v1.maintenance import check_maintenance

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars_result([]))
    current_user = _make_user()

    result = await check_maintenance(db=db, current_user=current_user)

    assert result["in_maintenance"] is False
    assert result["windows"] == []


# ─── create_maintenance_window (lines 93-94) ──────────────────────────────────


async def test_create_maintenance_window_success():
    """create_maintenance_window: 正常作成 → add/flush/refresh が呼ばれる（lines 93-94）"""
    from src.api.v1.maintenance import create_maintenance_window
    from src.schemas.maintenance_window import MaintenanceWindowCreate

    now = datetime.now(UTC)
    data = MaintenanceWindowCreate(
        name="本番メンテ",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=3),
    )
    current_user = _make_user()

    db = AsyncMock()
    db.add = MagicMock()

    result = await create_maintenance_window(data=data, db=db, current_user=current_user)

    db.add.assert_called_once()
    db.flush.assert_called_once()
    db.refresh.assert_called_once()


async def test_create_maintenance_window_invalid_time_raises_422():
    """create_maintenance_window: end_time <= start_time → 422"""
    from src.api.v1.maintenance import create_maintenance_window
    from src.schemas.maintenance_window import MaintenanceWindowCreate

    now = datetime.now(UTC)
    data = MaintenanceWindowCreate(
        name="不正メンテ",
        start_time=now + timedelta(hours=3),
        end_time=now + timedelta(hours=1),  # end < start
    )
    db = AsyncMock()
    current_user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await create_maintenance_window(data=data, db=db, current_user=current_user)

    assert exc_info.value.status_code == 422


async def test_create_maintenance_window_equal_times_raises_422():
    """create_maintenance_window: end_time == start_time → 422"""
    from src.api.v1.maintenance import create_maintenance_window
    from src.schemas.maintenance_window import MaintenanceWindowCreate

    now = datetime.now(UTC)
    data = MaintenanceWindowCreate(
        name="同時刻メンテ",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=1),  # equal
    )
    db = AsyncMock()
    current_user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await create_maintenance_window(data=data, db=db, current_user=current_user)

    assert exc_info.value.status_code == 422


# ─── get_maintenance_window (lines 107-113) ────────────────────────────────────


async def test_get_maintenance_window_found():
    """get_maintenance_window: 正常取得"""
    from src.api.v1.maintenance import get_maintenance_window

    w = _make_window()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(w))
    current_user = _make_user()

    result = await get_maintenance_window(
        window_id=w.window_id, db=db, current_user=current_user
    )

    assert result.window_id == w.window_id


async def test_get_maintenance_window_not_found():
    """get_maintenance_window: 404エラー（lines 107-113）"""
    from src.api.v1.maintenance import get_maintenance_window

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(None))
    current_user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await get_maintenance_window(
            window_id=uuid.uuid4(), db=db, current_user=current_user
        )

    assert exc_info.value.status_code == 404


# ─── update_maintenance_window (lines 127-137) ────────────────────────────────


async def test_update_maintenance_window_success():
    """update_maintenance_window: 正常更新（lines 127-137）"""
    from src.api.v1.maintenance import update_maintenance_window
    from src.schemas.maintenance_window import MaintenanceWindowUpdate

    w = _make_window(name="旧名称")
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(w))
    current_user = _make_user()

    data = MaintenanceWindowUpdate(name="新名称", is_active=False)
    result = await update_maintenance_window(
        window_id=w.window_id, data=data, db=db, current_user=current_user
    )

    assert w.name == "新名称"
    assert w.is_active is False
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(w)


async def test_update_maintenance_window_not_found():
    """update_maintenance_window: 404エラー（lines 127-132）"""
    from src.api.v1.maintenance import update_maintenance_window
    from src.schemas.maintenance_window import MaintenanceWindowUpdate

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(None))
    current_user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await update_maintenance_window(
            window_id=uuid.uuid4(),
            data=MaintenanceWindowUpdate(name="変更"),
            db=db,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404


async def test_update_maintenance_window_partial_update():
    """update_maintenance_window: exclude_unset で未指定フィールドは変更されない"""
    from src.api.v1.maintenance import update_maintenance_window
    from src.schemas.maintenance_window import MaintenanceWindowUpdate

    w = _make_window(name="元名称")
    w.is_active = True  # 変更しない
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(w))
    current_user = _make_user()

    # name だけ更新
    data = MaintenanceWindowUpdate(name="更新後")
    await update_maintenance_window(
        window_id=w.window_id, data=data, db=db, current_user=current_user
    )

    assert w.name == "更新後"


# ─── delete_maintenance_window (lines 150-156) ────────────────────────────────


async def test_delete_maintenance_window_success():
    """delete_maintenance_window: 正常削除（lines 150-156）"""
    from src.api.v1.maintenance import delete_maintenance_window

    w = _make_window()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(w))
    current_user = _make_user()

    result = await delete_maintenance_window(
        window_id=w.window_id, db=db, current_user=current_user
    )

    db.delete.assert_called_once_with(w)
    assert result is None


async def test_delete_maintenance_window_not_found():
    """delete_maintenance_window: 404エラー（lines 151-155）"""
    from src.api.v1.maintenance import delete_maintenance_window

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(None))
    current_user = _make_user()

    with pytest.raises(HTTPException) as exc_info:
        await delete_maintenance_window(
            window_id=uuid.uuid4(), db=db, current_user=current_user
        )

    assert exc_info.value.status_code == 404
