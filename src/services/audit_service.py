"""J-SOX準拠 SHA-256ハッシュチェーン監査サービス"""

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.audit import AuditLog
from src.schemas.audit import (
    ActionSummary,
    ComplianceReportResponse,
    SecurityEventSummary,
    UserActivityItem,
    UserActivityResponse,
)

logger = get_logger(__name__)


async def get_next_sequence(db: AsyncSession) -> int:
    """監査ログシーケンス番号を取得"""
    result = await db.execute(select(func.nextval("audit_log_seq")))
    return result.scalar_one()


async def get_last_hash(db: AsyncSession) -> str | None:
    """最新の監査ログハッシュを取得"""
    result = await db.execute(
        select(AuditLog.current_hash).order_by(AuditLog.sequence_number.desc()).limit(1)
    )
    return result.scalar_one_or_none()


def compute_hash(prev_hash: str | None, log_data: dict) -> str:
    """SHA-256ハッシュチェーン計算 - J-SOX改ざん防止"""
    chain_input = (prev_hash or "") + json.dumps(log_data, sort_keys=True, default=str)
    return hashlib.sha256(chain_input.encode("utf-8")).hexdigest()


async def record_audit_log(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    username: str | None = None,
    user_role: str | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    http_method: str | None = None,
    request_path: str | None = None,
    response_status: int | None = None,
    ip_address: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> AuditLog:
    """監査ログを記録（SHA-256ハッシュチェーン付き）"""
    created_at = datetime.now(UTC)
    sequence_number = await get_next_sequence(db)
    prev_hash = await get_last_hash(db)

    log_data = {
        "sequence_number": sequence_number,
        "created_at": created_at.isoformat(),
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    current_hash = compute_hash(prev_hash, log_data)

    audit_log = AuditLog(
        created_at=created_at,
        user_id=user_id,
        username=username,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        http_method=http_method,
        request_path=request_path,
        response_status=response_status,
        ip_address=ip_address,
        old_values=old_values,
        new_values=new_values,
        prev_log_hash=prev_hash,
        current_hash=current_hash,
        sequence_number=sequence_number,
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def verify_hash_chain(
    db: AsyncSession, start_seq: int, end_seq: int
) -> tuple[bool, int | None]:
    """ハッシュチェーン整合性検証"""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.sequence_number.between(start_seq, end_seq))
        .order_by(AuditLog.sequence_number)
    )
    logs = result.scalars().all()

    prev_hash = None
    for log in logs:
        log_data = {
            "sequence_number": log.sequence_number,
            "created_at": log.created_at.isoformat(),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
        }
        expected_hash = compute_hash(prev_hash, log_data)
        if expected_hash != log.current_hash:
            logger.warning("hash_chain_broken", sequence_number=log.sequence_number)
            return False, log.sequence_number
        prev_hash = log.current_hash

    return True, None


async def get_audit_logs(
    db: AsyncSession,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    """監査ログ一覧取得（フィルタ・ページネーション対応）"""
    query = select(AuditLog).order_by(AuditLog.sequence_number.desc())
    if entity_type:
        query = query.where(AuditLog.resource_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.resource_id == entity_id)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


# セキュリティイベントとして識別するアクション
_SECURITY_ACTIONS = {"LOGIN_FAILED", "UNAUTHORIZED_ACCESS", "FORBIDDEN_ATTEMPT"}
_PRIVILEGE_ACTIONS = {"PRIVILEGE_ESCALATION", "ROLE_CHANGE", "ADMIN_OVERRIDE"}


async def get_security_events_summary(
    db: AsyncSession,
    days: int = 30,
) -> SecurityEventSummary:
    """セキュリティイベントサマリー生成"""
    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(days=days)

    base_query = select(AuditLog).where(
        AuditLog.created_at >= period_start,
        AuditLog.created_at <= period_end,
    )

    # 認証失敗件数
    auth_fail_result = await db.execute(base_query.where(AuditLog.action.in_(_SECURITY_ACTIONS)))
    auth_failures = len(auth_fail_result.scalars().all())

    # 権限昇格件数
    priv_result = await db.execute(base_query.where(AuditLog.action.in_(_PRIVILEGE_ACTIONS)))
    privilege_escalations = len(priv_result.scalars().all())

    # アクション別集計（上位10件）
    action_counts = await db.execute(
        select(AuditLog.action, AuditLog.resource_type, func.count().label("cnt"))
        .where(AuditLog.created_at >= period_start, AuditLog.created_at <= period_end)
        .group_by(AuditLog.action, AuditLog.resource_type)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_actions = [
        ActionSummary(action=row.action, count=row.cnt, resource_type=row.resource_type)
        for row in action_counts
    ]

    total_events = auth_failures + privilege_escalations

    return SecurityEventSummary(
        period_start=period_start,
        period_end=period_end,
        auth_failures=auth_failures,
        privilege_escalations=privilege_escalations,
        total_events=total_events,
        top_actions=top_actions,
    )


async def get_user_activity_summary(
    db: AsyncSession,
    days: int = 30,
    limit: int = 20,
) -> UserActivityResponse:
    """ユーザーアクティビティサマリー生成"""
    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(days=days)

    # ユーザー別アクション件数 + 最終アクティビティ
    user_stats = await db.execute(
        select(
            AuditLog.user_id,
            AuditLog.username,
            AuditLog.user_role,
            func.count().label("action_count"),
            func.max(AuditLog.created_at).label("last_activity"),
        )
        .where(AuditLog.created_at >= period_start, AuditLog.created_at <= period_end)
        .group_by(AuditLog.user_id, AuditLog.username, AuditLog.user_role)
        .order_by(func.count().desc())
        .limit(limit)
    )

    items = [
        UserActivityItem(
            user_id=row.user_id,
            username=row.username,
            user_role=row.user_role,
            action_count=row.action_count,
            last_activity=row.last_activity,
        )
        for row in user_stats
    ]

    # ユニークユーザー数
    unique_users_result = await db.execute(
        select(func.count(distinct(AuditLog.user_id))).where(
            AuditLog.created_at >= period_start,
            AuditLog.created_at <= period_end,
            AuditLog.user_id.is_not(None),
        )
    )
    total_users = unique_users_result.scalar_one()

    return UserActivityResponse(
        period_start=period_start,
        period_end=period_end,
        total_users=total_users,
        items=items,
    )


async def generate_compliance_report(
    db: AsyncSession,
    days: int = 30,
    start_seq: int = 1,
    end_seq: int = 10000,
) -> ComplianceReportResponse:
    """J-SOXコンプライアンスレポート生成"""
    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(days=days)

    # 総ログ件数
    total_result = await db.execute(
        select(func.count()).where(
            AuditLog.created_at >= period_start,
            AuditLog.created_at <= period_end,
        )
    )
    total_logs = total_result.scalar_one()

    # ハッシュチェーン検証
    is_valid, first_invalid = await verify_hash_chain(db, start_seq, end_seq)

    # アクション別集計
    action_stats = await db.execute(
        select(AuditLog.action, AuditLog.resource_type, func.count().label("cnt"))
        .where(AuditLog.created_at >= period_start, AuditLog.created_at <= period_end)
        .group_by(AuditLog.action, AuditLog.resource_type)
        .order_by(func.count().desc())
    )
    actions_by_type = [
        ActionSummary(action=row.action, count=row.cnt, resource_type=row.resource_type)
        for row in action_stats
    ]

    # トップユーザー（上位5件）
    user_stats = await db.execute(
        select(
            AuditLog.user_id,
            AuditLog.username,
            AuditLog.user_role,
            func.count().label("action_count"),
            func.max(AuditLog.created_at).label("last_activity"),
        )
        .where(AuditLog.created_at >= period_start, AuditLog.created_at <= period_end)
        .group_by(AuditLog.user_id, AuditLog.username, AuditLog.user_role)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_users = [
        UserActivityItem(
            user_id=row.user_id,
            username=row.username,
            user_role=row.user_role,
            action_count=row.action_count,
            last_activity=row.last_activity,
        )
        for row in user_stats
    ]

    security_events = await get_security_events_summary(db, days=days)

    return ComplianceReportResponse(
        period_start=period_start,
        period_end=period_end,
        total_logs=total_logs,
        hash_chain_valid=is_valid,
        first_invalid_sequence=first_invalid,
        actions_by_type=actions_by_type,
        top_users=top_users,
        security_events=security_events,
    )


async def export_audit_logs(
    db: AsyncSession,
    entity_type: str | None = None,
    entity_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 1000,
) -> tuple[list[AuditLog], dict]:
    """監査ログエクスポート（J-SOX 7年保管対応）"""
    query = select(AuditLog).order_by(AuditLog.sequence_number)
    filters: dict = {}

    if entity_type:
        query = query.where(AuditLog.resource_type == entity_type)
        filters["entity_type"] = entity_type
    if entity_id:
        query = query.where(AuditLog.resource_id == entity_id)
        filters["entity_id"] = entity_id
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
        filters["start_date"] = start_date.isoformat()
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
        filters["end_date"] = end_date.isoformat()

    query = query.limit(limit)
    result = await db.execute(query)
    logs = list(result.scalars().all())
    return logs, filters
