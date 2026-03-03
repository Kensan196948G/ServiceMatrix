"""監査ログAPI - 一覧取得・フィルタ・整合性検証"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.user import User
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
