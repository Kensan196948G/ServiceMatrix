"""変更管理API - CRUD + リスク評価 + CAB承認"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.change import Change
from src.models.user import User, UserRole
from src.schemas.change import (
    CABApproval, ChangeCreate, ChangeResponse, ChangeStatusTransition, ChangeUpdate
)
from src.schemas.common import PaginatedResponse
from src.services import change_service

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("", response_model=PaginatedResponse[ChangeResponse])
async def list_changes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
):
    """変更一覧取得"""
    query = select(Change)
    if status_filter:
        query = query.where(Change.status == status_filter)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * size).limit(size).order_by(Change.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.post("", response_model=ChangeResponse, status_code=status.HTTP_201_CREATED)
async def create_change(
    data: ChangeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.CHANGE_MANAGER
    ))],
):
    """変更リクエスト作成（リスクスコア自動計算）"""
    change_data = data.model_dump(exclude_none=True)
    change_data["requested_by"] = current_user.user_id
    change = await change_service.create_change(db, change_data)
    return change


@router.get("/{change_id}", response_model=ChangeResponse)
async def get_change(
    change_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """変更詳細取得"""
    result = await db.execute(select(Change).where(Change.change_id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="変更が見つかりません")
    return change


@router.patch("/{change_id}", response_model=ChangeResponse)
async def update_change(
    change_id: uuid.UUID,
    data: ChangeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.CHANGE_MANAGER
    ))],
):
    """変更更新"""
    result = await db.execute(select(Change).where(Change.change_id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="変更が見つかりません")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(change, field, value)
    await db.flush()
    await db.refresh(change)
    return change


@router.post("/{change_id}/transitions", response_model=ChangeResponse)
async def transition_change_status(
    change_id: uuid.UUID,
    transition: ChangeStatusTransition,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.CHANGE_MANAGER
    ))],
):
    """変更ステータス遷移"""
    result = await db.execute(select(Change).where(Change.change_id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="変更が見つかりません")

    try:
        change = await change_service.transition_change_status(db, change, transition.new_status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return change


@router.post("/{change_id}/cab-approval", response_model=ChangeResponse)
async def cab_approval(
    change_id: uuid.UUID,
    approval: CABApproval,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.CHANGE_MANAGER
    ))],
):
    """CAB承認・却下"""
    result = await db.execute(select(Change).where(Change.change_id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="変更が見つかりません")

    try:
        change = await change_service.approve_by_cab(
            db, change, current_user.user_id, approval.approved, approval.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return change
