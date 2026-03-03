"""監査ログAPI - 一覧取得・フィルタ・整合性検証・J-SOXコンプライアンスレポート"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.user import User
from src.schemas.audit import (
    AuditExportResponse,
    AuditLogResponse,
    ComplianceReportResponse,
    HashChainVerifyResponse,
    SecurityEventSummary,
    UserActivityResponse,
)
from src.services.audit_service import (
    export_audit_logs,
    generate_compliance_report,
    get_audit_logs,
    get_security_events_summary,
    get_user_activity_summary,
    verify_hash_chain,
)

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
    "/report/compliance",
    response_model=ComplianceReportResponse,
    summary="J-SOXコンプライアンスレポート",
    description="指定期間のJ-SOX準拠コンプライアンスレポートを生成します。ハッシュチェーン検証・アクション集計・セキュリティイベントを含みます。",
)
async def get_compliance_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="レポート対象期間（日数）"),
    start_seq: int = Query(1, ge=1, description="ハッシュチェーン検証開始シーケンス"),
    end_seq: int = Query(10000, ge=1, description="ハッシュチェーン検証終了シーケンス"),
) -> ComplianceReportResponse:
    return await generate_compliance_report(db, days=days, start_seq=start_seq, end_seq=end_seq)


@router.get(
    "/report/security-events",
    response_model=SecurityEventSummary,
    summary="セキュリティイベントサマリー",
    description="認証失敗・権限昇格などのセキュリティイベントをサマリーします。",
)
async def get_security_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="レポート対象期間（日数）"),
) -> SecurityEventSummary:
    return await get_security_events_summary(db, days=days)


@router.get(
    "/report/user-activity",
    response_model=UserActivityResponse,
    summary="ユーザーアクティビティレポート",
    description="ユーザー別のアクション件数・最終アクティビティを集計します。",
)
async def get_user_activity_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="レポート対象期間（日数）"),
    limit: int = Query(20, ge=1, le=100, description="取得件数上限"),
) -> UserActivityResponse:
    return await get_user_activity_summary(db, days=days, limit=limit)


@router.get(
    "/export",
    response_model=AuditExportResponse,
    summary="監査ログエクスポート（7年保管対応）",
    description="J-SOX 7年保管要件対応の監査ログバルクエクスポート。フィルタ・日付範囲指定可能。",
)
async def export_audit_log_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
) -> AuditExportResponse:
    logs, filters_applied = await export_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    records = [AuditLogResponse.model_validate(log) for log in logs]
    from datetime import UTC

    return AuditExportResponse(
        exported_at=datetime.now(UTC),
        total_records=len(records),
        filters_applied=filters_applied,
        records=records,
    )
