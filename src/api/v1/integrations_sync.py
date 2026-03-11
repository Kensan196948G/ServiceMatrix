"""外部ITSM双方向同期API - Jira/ServiceNow同期基盤"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import require_role
from src.models.incident import Incident
from src.models.user import User, UserRole
from src.services.integration_sync_service import integration_sync_service

router = APIRouter(prefix="/integrations/sync", tags=["integrations-sync"])

# RBAC: admin/manager のみ許可
_ALLOWED_ROLES = (UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER)


# ---------- Schemas ----------


class ConnectionTestRequest(BaseModel):
    integration_type: str  # "jira" | "servicenow"
    base_url: str
    api_key: str


class SyncTriggerRequest(BaseModel):
    config_id: str
    incident_id: str
    integration_type: str = "jira"  # "jira" | "servicenow"


class SyncConfigResponse(BaseModel):
    config_id: str
    integration_type: str
    name: str
    is_active: bool
    sync_interval_minutes: int


class SyncStatusResponse(BaseModel):
    total_synced: int
    last_sync_at: str | None
    pending_count: int
    failed_count: int
    integrations: list[dict]


# ---------- Endpoints ----------


@router.get("/configs", response_model=list[SyncConfigResponse])
async def list_sync_configs(
    current_user: Annotated[User, Depends(require_role(*_ALLOWED_ROLES))],
) -> list[dict[str, Any]]:
    """同期設定一覧を取得"""
    # 実際の実装では DB から取得する
    return [
        {
            "config_id": "00000000-0000-0000-0000-000000000001",
            "integration_type": "jira",
            "name": "Jira Production",
            "is_active": True,
            "sync_interval_minutes": 30,
        },
        {
            "config_id": "00000000-0000-0000-0000-000000000002",
            "integration_type": "servicenow",
            "name": "ServiceNow ITSM",
            "is_active": False,
            "sync_interval_minutes": 60,
        },
    ]


@router.post("/test-connection")
async def test_connection(
    request: ConnectionTestRequest,
    current_user: Annotated[User, Depends(require_role(*_ALLOWED_ROLES))],
) -> dict[str, Any]:
    """外部システムへの接続テスト"""
    result = await integration_sync_service.test_connection(
        integration_type=request.integration_type,
        base_url=request.base_url,
        api_key=request.api_key,
    )
    return {
        "integration_type": request.integration_type,
        "base_url": request.base_url,
        **result,
    }


@router.post("/trigger")
async def trigger_sync(
    request: SyncTriggerRequest,
    current_user: Annotated[User, Depends(require_role(*_ALLOWED_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """手動同期トリガー"""
    # integration_type を先に検証し、DB アクセス前に不正入力を弾く
    if request.integration_type not in ("jira", "servicenow"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown integration_type: {request.integration_type}",
        )

    # str → UUID 変換（UUID カラムとの型不一致による StatementError を防ぐ）
    try:
        incident_uuid = uuid.UUID(request.incident_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid UUID format: {request.incident_id}",
        ) from exc

    row = await db.execute(select(Incident).where(Incident.incident_id == incident_uuid))
    incident = row.scalar_one_or_none()
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident not found: {request.incident_id}",
        )

    incident_data = {
        "incident_id": str(incident.incident_id),
        "title": incident.title,
        "description": incident.description or "",
        "priority": incident.priority,
        "status": incident.status,
    }
    config = {"config_id": request.config_id}

    if request.integration_type == "jira":
        result = await integration_sync_service.sync_incident_to_jira(
            incident_data=incident_data,
            config=config,
        )
    else:
        result = await integration_sync_service.sync_incident_to_servicenow(
            incident_data=incident_data,
            config=config,
        )

    return {
        "config_id": request.config_id,
        "incident_id": request.incident_id,
        "integration_type": request.integration_type,
        **result,
    }


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: Annotated[User, Depends(require_role(*_ALLOWED_ROLES))],
) -> dict[str, Any]:
    """同期ステータスを取得"""
    return {
        "total_synced": 0,
        "last_sync_at": None,
        "pending_count": 0,
        "failed_count": 0,
        "integrations": [
            {
                "type": "jira",
                "status": "active",
                "last_sync": None,
            },
            {
                "type": "servicenow",
                "status": "inactive",
                "last_sync": None,
            },
        ],
    }
