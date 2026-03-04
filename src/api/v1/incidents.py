"""インシデント管理API - CRUD + ステータス遷移 + SLA"""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.incident import Incident
from src.models.user import User, UserRole
from src.schemas.common import PaginatedResponse
from src.schemas.incident import (
    IncidentBulkAssign,
    IncidentCreate,
    IncidentResponse,
    IncidentStatusTransition,
    IncidentUpdate,
)
from src.services import incident_service
from src.services.ai_triage_service import ai_triage_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get(
    "",
    response_model=PaginatedResponse[IncidentResponse],
    summary="インシデント一覧取得",
    description="フィルタ・ページネーション対応のインシデント一覧を返します。",
)
async def list_incidents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
):
    """インシデント一覧取得（ページネーション）"""
    query = select(Incident)
    if status_filter:
        query = query.where(Incident.status == status_filter)
    if priority:
        query = query.where(Incident.priority == priority)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * size).limit(size).order_by(Incident.created_at.desc())
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
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="インシデント作成",
    description="新規インシデントを作成します。SLA自動計算・優先度設定に対応。",
)
async def create_incident(
    data: IncidentCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
):
    """インシデント作成"""
    incident = await incident_service.create_incident(db, data.model_dump(exclude_none=True))
    background_tasks.add_task(
        ai_triage_service.apply_triage_to_incident, db, str(incident.incident_id)
    )
    return incident


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="インシデント詳細取得",
    description="指定されたIDのインシデント詳細を返します。",
)
async def get_incident(
    incident_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """インシデント詳細取得"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )
    return incident


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="インシデント更新",
    description="指定されたIDのインシデントを部分更新します。",
)
async def update_incident(
    incident_id: uuid.UUID,
    data: IncidentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
):
    """インシデント更新"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(incident, field, value)
    await db.flush()
    await db.refresh(incident)
    return incident


@router.post(
    "/{incident_id}/transitions",
    response_model=IncidentResponse,
    summary="インシデントステータス遷移",
    description="インシデントのステータスをITILワークフローに従って遷移させます。",
)
async def transition_incident_status(
    incident_id: uuid.UUID,
    transition: IncidentStatusTransition,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
):
    """インシデントステータス遷移"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )

    try:
        incident = await incident_service.transition_status(
            db, incident, transition.new_status, str(current_user.user_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return incident


@router.patch(
    "/bulk/assign",
    summary="インシデント一括担当者割り当て",
    description="複数のインシデントに対して一括で担当者・担当チームを割り当てます。",
)
async def bulk_assign_incidents(
    data: IncidentBulkAssign,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
) -> dict:
    """インシデント一括担当者割り当て"""
    updated_ids = []
    for incident_id in data.incident_ids:
        result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            if data.assigned_to is not None:
                incident.assigned_to = data.assigned_to
            if data.assigned_team_id is not None:
                incident.assigned_team_id = data.assigned_team_id
            await db.flush()
            updated_ids.append(str(incident_id))
    return {"updated": len(updated_ids), "incident_ids": updated_ids}
