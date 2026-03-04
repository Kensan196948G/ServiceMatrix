"""メンテナンスウィンドウ管理API"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.maintenance_window import MaintenanceWindow
from src.models.user import User, UserRole
from src.schemas.maintenance_window import (
    MaintenanceWindowCreate,
    MaintenanceWindowResponse,
    MaintenanceWindowUpdate,
)

router = APIRouter(prefix="/maintenance-windows", tags=["メンテナンスウィンドウ"])


@router.get("", response_model=list[MaintenanceWindowResponse])
async def list_maintenance_windows(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MaintenanceWindow]:
    """メンテナンスウィンドウ一覧（全ユーザー閲覧可）"""
    result = await db.execute(
        select(MaintenanceWindow).order_by(MaintenanceWindow.start_time.desc())
    )
    return list(result.scalars().all())


@router.get("/active", response_model=list[MaintenanceWindowResponse])
async def list_active_windows(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MaintenanceWindow]:
    """現在アクティブなメンテナンスウィンドウ一覧"""
    now = datetime.now(UTC)
    result = await db.execute(
        select(MaintenanceWindow).where(
            MaintenanceWindow.is_active.is_(True),
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= now,
        )
    )
    return list(result.scalars().all())


@router.get("/check")
async def check_maintenance(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """現在メンテナンス中かチェック"""
    now = datetime.now(UTC)
    result = await db.execute(
        select(MaintenanceWindow).where(
            MaintenanceWindow.is_active.is_(True),
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= now,
        )
    )
    windows = list(result.scalars().all())
    return {
        "in_maintenance": len(windows) > 0,
        "windows": [MaintenanceWindowResponse.model_validate(w).model_dump() for w in windows],
    }


@router.post("", response_model=MaintenanceWindowResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_window(
    data: MaintenanceWindowCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.CHANGE_MANAGER))],
) -> MaintenanceWindow:
    """メンテナンスウィンドウ作成（SYSTEM_ADMIN / CHANGE_MANAGER）"""
    if data.end_time <= data.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time は start_time より後にしてください",
        )
    window = MaintenanceWindow(
        window_id=uuid.uuid4(),
        created_by=current_user.user_id,
        **data.model_dump(),
    )
    db.add(window)
    await db.flush()
    await db.refresh(window)
    return window


@router.get("/{window_id}", response_model=MaintenanceWindowResponse)
async def get_maintenance_window(
    window_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenanceWindow:
    """メンテナンスウィンドウ詳細"""
    result = await db.execute(
        select(MaintenanceWindow).where(MaintenanceWindow.window_id == window_id)
    )
    window = result.scalar_one_or_none()
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メンテナンスウィンドウが見つかりません",
        )
    return window


@router.patch("/{window_id}", response_model=MaintenanceWindowResponse)
async def update_maintenance_window(
    window_id: uuid.UUID,
    data: MaintenanceWindowUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.CHANGE_MANAGER))],
) -> MaintenanceWindow:
    """メンテナンスウィンドウ更新（SYSTEM_ADMIN / CHANGE_MANAGER）"""
    result = await db.execute(
        select(MaintenanceWindow).where(MaintenanceWindow.window_id == window_id)
    )
    window = result.scalar_one_or_none()
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メンテナンスウィンドウが見つかりません",
        )
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(window, field, value)
    await db.flush()
    await db.refresh(window)
    return window


@router.delete("/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_window(
    window_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> None:
    """メンテナンスウィンドウ削除（SYSTEM_ADMINのみ）"""
    result = await db.execute(
        select(MaintenanceWindow).where(MaintenanceWindow.window_id == window_id)
    )
    window = result.scalar_one_or_none()
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メンテナンスウィンドウが見つかりません",
        )
    await db.delete(window)
