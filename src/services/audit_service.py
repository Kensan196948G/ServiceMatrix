"""J-SOX準拠 SHA-256ハッシュチェーン監査サービス"""
import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.audit import AuditLog

logger = get_logger(__name__)


async def get_next_sequence(db: AsyncSession) -> int:
    """監査ログシーケンス番号を取得"""
    result = await db.execute(select(func.nextval("audit_log_seq")))
    return result.scalar_one()


async def get_last_hash(db: AsyncSession) -> str | None:
    """最新の監査ログハッシュを取得"""
    result = await db.execute(
        select(AuditLog.current_hash)
        .order_by(AuditLog.sequence_number.desc())
        .limit(1)
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
