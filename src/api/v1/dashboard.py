"""ダッシュボードAPI - ロール別ウィジェット設定"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.middleware.rbac import get_current_user
from src.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_WIDGET_MAP: dict[str, list[str]] = {
    "OPERATOR": ["sla_alerts", "my_incidents", "open_incidents", "sla_summary"],
    "SERVICE_MANAGER": ["pending_approvals", "open_changes", "sla_summary", "incident_trend"],
    "CHANGE_MANAGER": ["pending_approvals", "open_changes", "sla_summary", "incident_trend"],
    "SYSTEM_ADMIN": ["system_stats", "audit_summary", "all_incidents", "all_changes"],
    "VIEWER": ["open_incidents", "sla_summary"],
}


@router.get("/widgets", summary="ロール別ウィジェット設定取得")
async def get_widgets(
    current_user: Annotated[User, Depends(get_current_user)],
    role: str = Query(default="VIEWER"),
) -> dict:
    """ロールに応じたダッシュボードウィジェット一覧を返す"""
    normalized = role.upper()
    widgets = _WIDGET_MAP.get(normalized, _WIDGET_MAP["VIEWER"])
    return {"role": normalized, "widgets": widgets}
