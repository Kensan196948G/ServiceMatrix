"""変更管理API - CRUD + リスク評価 + CAB承認"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.change import Change
from src.models.user import User, UserRole
from src.schemas.change import (
    CABApproval,
    ChangeCreate,
    ChangeResponse,
    ChangeStatusTransition,
    ChangeUpdate,
)
from src.schemas.change_risk import RiskAssessmentResultSchema
from src.schemas.common import PaginatedResponse
from src.services import change_service
from src.services.change_risk_service import change_risk_service

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get(
    "",
    response_model=PaginatedResponse[ChangeResponse],
    summary="変更一覧取得",
    description="フィルタ・ページネーション対応の変更リクエスト一覧を返します。",
)
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


@router.post(
    "",
    response_model=ChangeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="変更リクエスト作成",
    description="新規変更リクエストを作成します。リスクスコアが自動計算されます。",
)
async def create_change(
    data: ChangeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.CHANGE_MANAGER)
        ),
    ],
):
    """変更リクエスト作成（リスクスコア自動計算）"""
    change_data = data.model_dump(exclude_none=True)
    change_data["requested_by"] = current_user.user_id
    change = await change_service.create_change(db, change_data)
    return change


@router.get(
    "/calendar",
    summary="変更カレンダー取得",
    description="指定期間のスケジュール済み変更一覧を日付でグループ化して返します。",
)
async def get_change_calendar(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start_date: date = Query(..., description="開始日 YYYY-MM-DD"),
    end_date: date = Query(..., description="終了日 YYYY-MM-DD"),
):
    """指定期間の変更カレンダー（スケジュール済み変更一覧）"""
    from datetime import datetime, timezone

    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)

    query = (
        select(Change)
        .where(
            Change.scheduled_start_at >= start_dt,
            Change.scheduled_start_at <= end_dt,
        )
        .order_by(Change.scheduled_start_at)
    )
    result = await db.execute(query)
    changes = result.scalars().all()

    # 日付でグループ化
    grouped: dict[str, list] = {}
    for change in changes:
        day = change.scheduled_start_at.date().isoformat()
        if day not in grouped:
            grouped[day] = []
        grouped[day].append({
            "change_id": str(change.change_id),
            "change_number": change.change_number,
            "title": change.title,
            "status": change.status,
            "change_type": change.change_type,
            "risk_level": change.risk_level,
            "scheduled_start_at": change.scheduled_start_at.isoformat(),
            "scheduled_end_at": change.scheduled_end_at.isoformat() if change.scheduled_end_at else None,
        })

    events = [{"date": day, "changes": items} for day, items in sorted(grouped.items())]

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total": len(changes),
        "events": events,
    }


@router.get(
    "/{change_id}",
    response_model=ChangeResponse,
    summary="変更詳細取得",
    description="指定されたIDの変更リクエスト詳細を返します。",
)
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


@router.patch(
    "/{change_id}",
    response_model=ChangeResponse,
    summary="変更更新",
    description="指定されたIDの変更リクエストを部分更新します。",
)
async def update_change(
    change_id: uuid.UUID,
    data: ChangeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.CHANGE_MANAGER)
        ),
    ],
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


@router.post(
    "/{change_id}/transitions",
    response_model=ChangeResponse,
    summary="変更ステータス遷移",
    description="変更リクエストのステータスをCABワークフローに従って遷移させます。",
)
async def transition_change_status(
    change_id: uuid.UUID,
    transition: ChangeStatusTransition,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.CHANGE_MANAGER)
        ),
    ],
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


@router.post(
    "/{change_id}/cab-approval",
    response_model=ChangeResponse,
    summary="CAB承認・却下",
    description=("Change Advisory Board (CAB) による変更リクエストの承認または却下を行います。"),
)
async def cab_approval(
    change_id: uuid.UUID,
    approval: CABApproval,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.CHANGE_MANAGER))
    ],
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


@router.post(
    "/{change_id}/risk-assessment",
    response_model=RiskAssessmentResultSchema,
    summary="リスク自動評価",
    description="Changeのリスクを自動評価します。",
)
async def assess_change_risk(
    change_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RiskAssessmentResultSchema:
    try:
        result = await change_risk_service.assess_risk(db, str(change_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return RiskAssessmentResultSchema(**result.__dict__)
