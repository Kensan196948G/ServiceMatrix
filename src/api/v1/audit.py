"""監査ログAPI - 一覧取得・フィルタ・整合性検証・CSV export・統計"""

import csv
import io
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.audit import AuditLog
from src.models.user import User, UserRole
from src.schemas.audit import AuditLogResponse, HashChainVerifyResponse
from src.services.audit_service import get_audit_logs, verify_hash_chain

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get(
    "/logs",
    response_model=list[AuditLogResponse],
    summary="監査ログ一覧",
    description="監査ログを取得します。entity_type・entity_idでフィルタ可能。",
)
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> list[AuditLogResponse]:
    logs = await get_audit_logs(
        db, entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset
    )
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get(
    "/logs/{entity_type}/{entity_id}",
    response_model=list[AuditLogResponse],
    summary="エンティティ別監査ログ",
    description="指定エンティティの監査ログを取得します。",
)
async def get_entity_audit_logs(
    entity_type: str,
    entity_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> list[AuditLogResponse]:
    logs = await get_audit_logs(
        db, entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset
    )
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.post(
    "/verify-chain",
    response_model=HashChainVerifyResponse,
    summary="ハッシュチェーン整合性検証",
    description="監査ログのハッシュチェーン整合性を検証します。改ざん検知に使用。",
)
async def verify_audit_chain(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start_seq: int = Query(1, ge=1),
    end_seq: int = Query(100, ge=1),
) -> HashChainVerifyResponse:
    is_valid, first_invalid = await verify_hash_chain(db, start_seq, end_seq)
    checked_count = max(0, end_seq - start_seq + 1)
    if is_valid:
        message = f"シーケンス {start_seq}〜{end_seq} のハッシュチェーンは正常です。"
    else:
        message = f"シーケンス {first_invalid} でハッシュチェーンの不整合が検出されました。"
    return HashChainVerifyResponse(
        is_valid=is_valid,
        checked_count=checked_count,
        first_invalid_sequence=first_invalid,
        message=message,
    )


@router.get(
    "/logs/export",
    summary="監査ログCSVエクスポート",
    description="監査ログをCSV形式でエクスポートします。",
)
async def export_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER)),
    ],
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(5000, le=10000),
) -> Response:
    query = select(AuditLog).order_by(AuditLog.sequence_number.desc())
    if entity_type:
        query = query.where(AuditLog.resource_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.resource_id == entity_id)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)
    query = query.limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    output = io.StringIO()
    fieldnames = ["timestamp", "user", "action", "resource_type", "resource_id", "details"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for log in logs:
        writer.writerow(
            {
                "timestamp": log.created_at.isoformat(),
                "user": log.username or str(log.user_id) if log.user_id else "",
                "action": log.action,
                "resource_type": log.resource_type or "",
                "resource_id": log.resource_id or "",
                "details": str(log.new_values) if log.new_values else "",
            }
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get(
    "/stats",
    summary="監査ログ統計",
    description="監査ログの統計情報を返します。",
)
async def get_audit_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    total_result = await db.execute(select(func.count()).select_from(AuditLog))
    total_operations: int = total_result.scalar_one() or 0

    unique_users_result = await db.execute(
        select(func.count(distinct(AuditLog.user_id))).where(AuditLog.user_id.isnot(None))
    )
    unique_users: int = unique_users_result.scalar_one() or 0

    by_action_result = await db.execute(
        select(AuditLog.action, func.count().label("cnt")).group_by(AuditLog.action)
    )
    by_action: dict[str, int] = {row.action: row.cnt for row in by_action_result}

    by_resource_result = await db.execute(
        select(AuditLog.resource_type, func.count().label("cnt"))
        .where(AuditLog.resource_type.isnot(None))
        .group_by(AuditLog.resource_type)
    )
    by_resource: dict[str, int] = {row.resource_type: row.cnt for row in by_resource_result}

    recent_result = await db.execute(
        select(AuditLog).order_by(AuditLog.sequence_number.desc()).limit(10)
    )
    recent_logs = recent_result.scalars().all()
    recent_activity = [
        {
            "timestamp": log.created_at.isoformat(),
            "user": log.username or str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
        }
        for log in recent_logs
    ]

    return {
        "total_operations": total_operations,
        "unique_users": unique_users,
        "by_action": by_action,
        "by_resource": by_resource,
        "recent_activity": recent_activity,
    }
