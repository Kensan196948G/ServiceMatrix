"""外部統合設定API - Jira/ServiceNow統合フレームワーク"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.incident import Incident, IncidentPriority, IncidentStatus
from src.models.integration import IntegrationConfig
from src.models.user import User, UserRole

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ---------- Schemas ----------


class IntegrationCreate(BaseModel):
    integration_type: str
    name: str
    base_url: str | None = None
    api_key: str | None = None
    username: str | None = None
    webhook_secret: str | None = None
    is_active: bool = True
    sync_interval_minutes: int = 30
    config_json: str | None = None


class IntegrationUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    username: str | None = None
    webhook_secret: str | None = None
    is_active: bool | None = None
    sync_interval_minutes: int | None = None
    config_json: str | None = None


def _to_dict(cfg: IntegrationConfig) -> dict[str, Any]:
    return {
        "config_id": str(cfg.config_id),
        "integration_type": cfg.integration_type,
        "name": cfg.name,
        "base_url": cfg.base_url,
        "username": cfg.username,
        "is_active": cfg.is_active,
        "sync_interval_minutes": cfg.sync_interval_minutes,
        "last_synced_at": cfg.last_synced_at.isoformat() if cfg.last_synced_at else None,
        "created_at": cfg.created_at.isoformat() if cfg.created_at else None,
    }


# ---------- Endpoints ----------


@router.get("", summary="統合設定一覧")
async def list_integrations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    rows = (await db.execute(select(IntegrationConfig))).scalars().all()
    return [_to_dict(r) for r in rows]


@router.post("", summary="統合設定追加", status_code=status.HTTP_201_CREATED)
async def create_integration(
    payload: IntegrationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> dict[str, Any]:
    cfg = IntegrationConfig(**payload.model_dump())
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return _to_dict(cfg)


@router.patch("/{config_id}", summary="統合設定更新")
async def update_integration(
    config_id: uuid.UUID,
    payload: IntegrationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> dict[str, Any]:
    cfg = await db.get(IntegrationConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration not found")
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(cfg, key, val)
    await db.commit()
    await db.refresh(cfg)
    return _to_dict(cfg)


@router.delete("/{config_id}", summary="統合設定削除", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    config_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> None:
    cfg = await db.get(IntegrationConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.delete(cfg)
    await db.commit()


@router.post("/{config_id}/test", summary="接続テスト（モック）")
async def test_integration(
    config_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    cfg = await db.get(IntegrationConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration not found")
    # モック: 常に成功を返す
    return {
        "success": True,
        "message": f"{cfg.name} への接続テストに成功しました",
        "latency_ms": 42,
    }  # noqa: E501


@router.get("/{config_id}/sync-log", summary="同期ログ（最新20件）")
async def get_sync_log(
    config_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    cfg = await db.get(IntegrationConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration not found")
    # モック: ダミーログを返す
    return [
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": "sync_completed",
            "records_processed": 0,
            "status": "success",
        }
    ]


# ---------- Webhook Receivers ----------


@router.post("/webhook/jira", summary="Jira Webhookエンドポイント", status_code=status.HTTP_200_OK)
async def webhook_jira(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Jiraからのissue_created/issue_updatedイベントを受け取りIncidentに変換"""
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    event = body.get("webhookEvent", "")
    issue = body.get("issue", {})
    fields = issue.get("fields", {})

    if event in ("jira:issue_created", "jira:issue_updated") and issue:
        incident = Incident(
            incident_number=f"INC-JIRA-{issue.get('key', uuid.uuid4().hex[:8])}",
            title=fields.get("summary", "Jira Issue")[:500],
            description=fields.get("description") or "",
            priority=IncidentPriority.P3,
            status=IncidentStatus.NEW,
        )
        db.add(incident)
        await db.commit()
        return {"received": True, "incident_id": str(incident.incident_id)}

    return {"received": True, "skipped": True}


@router.post(
    "/webhook/servicenow",
    summary="ServiceNow Webhookエンドポイント",
    status_code=status.HTTP_200_OK,
)
async def webhook_servicenow(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """ServiceNowのincident_createdイベントを受け取りIncidentに変換"""
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    if body.get("event") == "incident_created":
        record = body.get("record", {})
        incident = Incident(
            incident_number=f"INC-SNW-{record.get('sys_id', uuid.uuid4().hex[:8])[:8]}",
            title=record.get("short_description", "ServiceNow Incident")[:500],
            description=record.get("description") or "",
            priority=IncidentPriority.P3,
            status=IncidentStatus.NEW,
        )
        db.add(incident)
        await db.commit()
        return {"received": True, "incident_id": str(incident.incident_id)}

    return {"received": True, "skipped": True}
