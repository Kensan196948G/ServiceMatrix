"""外部ITSM双方向同期API - Jira/ServiceNow同期基盤"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.middleware.rbac import require_role
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
) -> dict[str, Any]:
    """手動同期トリガー"""
    incident_data = {
        "incident_id": request.incident_id,
        "config_id": request.config_id,
    }
    config = {"config_id": request.config_id}

    if request.integration_type == "jira":
        result = await integration_sync_service.sync_incident_to_jira(
            incident_data=incident_data,
            config=config,
        )
    elif request.integration_type == "servicenow":
        result = await integration_sync_service.sync_incident_to_servicenow(
            incident_data=incident_data,
            config=config,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown integration_type: {request.integration_type}",
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
