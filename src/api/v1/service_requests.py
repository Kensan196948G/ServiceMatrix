"""サービスリクエスト管理API - CRUD + ステータス遷移"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.service_request import ServiceRequest
from src.models.user import User, UserRole
from src.schemas.common import PaginatedResponse
from src.schemas.service_request import (
    ServiceRequestApprovalAction,
    ServiceRequestCompleteAction,
    ServiceRequestCreate,
    ServiceRequestResponse,
    ServiceRequestStatusTransition,
    ServiceRequestToIncidentRequest,
    ServiceRequestToIncidentResponse,
    ServiceRequestUpdate,
)
from src.services import incident_service, service_request_service

router = APIRouter(prefix="/service-requests", tags=["service-requests"])


@router.get("", response_model=PaginatedResponse[ServiceRequestResponse])
async def list_service_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """サービスリクエスト一覧取得"""
    items, total = await service_request_service.get_service_requests(
        db, status_filter, skip, limit
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1 if limit else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
    )


@router.post("", response_model=ServiceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_service_request(
    data: ServiceRequestCreate,
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
    """サービスリクエスト作成"""
    sr = await service_request_service.create_service_request(
        db, data.model_dump(exclude_none=True)
    )
    return sr


@router.get("/{request_id}", response_model=ServiceRequestResponse)
async def get_service_request(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """サービスリクエスト詳細取得"""
    sr = await service_request_service.get_service_request(db, request_id)
    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サービスリクエストが見つかりません",
        )
    return sr


@router.patch("/{request_id}", response_model=ServiceRequestResponse)
async def update_service_request(
    request_id: uuid.UUID,
    data: ServiceRequestUpdate,
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
    """サービスリクエスト更新"""
    sr = await service_request_service.update_service_request(
        db, request_id, data.model_dump(exclude_none=True)
    )
    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サービスリクエストが見つかりません",
        )
    return sr


@router.post("/{request_id}/transitions", response_model=ServiceRequestResponse)
async def transition_service_request_status(
    request_id: uuid.UUID,
    transition: ServiceRequestStatusTransition,
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
    """サービスリクエストステータス遷移"""
    try:
        sr = await service_request_service.transition_service_request_status(
            db, request_id, transition.target_status, transition.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return sr


@router.post("/{request_id}/submit", response_model=ServiceRequestResponse)
async def submit_service_request(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """申請提出（New→Pending_Approval）"""
    try:
        sr = await service_request_service.submit_request(db, request_id, str(current_user.user_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return sr


@router.post("/{request_id}/approve", response_model=ServiceRequestResponse)
async def approve_service_request(
    request_id: uuid.UUID,
    action: ServiceRequestApprovalAction,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER)),
    ],
):
    """承認（Pending_Approval→Approved）"""
    try:
        sr = await service_request_service.approve_request(
            db, request_id, str(current_user.user_id), action.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return sr


@router.post("/{request_id}/reject", response_model=ServiceRequestResponse)
async def reject_service_request(
    request_id: uuid.UUID,
    action: ServiceRequestApprovalAction,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER)),
    ],
):
    """却下（Pending_Approval→Rejected）"""
    try:
        sr = await service_request_service.reject_request(
            db, request_id, str(current_user.user_id), action.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return sr


@router.post("/{request_id}/start", response_model=ServiceRequestResponse)
async def start_service_request_fulfillment(
    request_id: uuid.UUID,
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
    """実行開始（Approved→In_Fulfillment）"""
    try:
        sr = await service_request_service.start_fulfillment(db, request_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return sr


@router.post("/{request_id}/complete", response_model=ServiceRequestResponse)
async def complete_service_request(
    request_id: uuid.UUID,
    action: ServiceRequestCompleteAction,
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
    """完了/失敗（In_Fulfillment→Fulfilled/Failed）"""
    try:
        sr = await service_request_service.complete_request(db, request_id, action.success)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return sr


@router.post(
    "/{request_id}/create-incident",
    response_model=ServiceRequestToIncidentResponse,
    summary="SRからインシデント自動生成",
    description="サービスリクエストの内容をもとにインシデントを自動生成します。",
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_from_sr(
    request_id: uuid.UUID,
    body: ServiceRequestToIncidentRequest,
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
) -> ServiceRequestToIncidentResponse:
    """サービスリクエストからインシデントを自動生成"""
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.request_id == request_id))
    sr = result.scalar_one_or_none()
    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サービスリクエストが見つかりません",
        )

    description_parts = [
        f"サービスリクエスト {sr.request_number} から自動生成されたインシデントです。"
    ]
    if sr.description:
        description_parts.append(f"\n【SR詳細】\n{sr.description}")
    if body.additional_notes:
        description_parts.append(f"\n【追記】\n{body.additional_notes}")

    incident_data = {
        "title": f"[SR] {sr.title}",
        "description": "\n".join(description_parts),
        "priority": body.priority,
        "category": body.category or sr.request_type,
        "reported_by": sr.requested_by,
    }
    incident = await incident_service.create_incident(db, incident_data)
    await db.flush()

    return ServiceRequestToIncidentResponse(
        incident_id=incident.incident_id,
        incident_number=incident.incident_number,
        service_request_id=sr.request_id,
        service_request_number=sr.request_number,
        message=f"インシデント {incident.incident_number} を作成しました。",
    )
