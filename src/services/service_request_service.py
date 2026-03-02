"""サービスリクエスト管理ビジネスロジック"""
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.service_request import ServiceRequest
from src.schemas.service_request import VALID_SR_TRANSITIONS
from src.services import audit_service

logger = get_logger(__name__)


async def _get_next_sr_number(db: AsyncSession) -> str:
    """SR-YYYY-NNNNNN形式のサービスリクエスト番号を生成"""
    year = datetime.now(UTC).year
    result = await db.execute(select(func.nextval("service_request_seq")))
    seq = result.scalar_one()
    return f"SR-{year}-{seq:06d}"


async def create_service_request(db: AsyncSession, data: dict[str, Any]) -> ServiceRequest:
    """サービスリクエストを作成する"""
    request_number = await _get_next_sr_number(db)
    sr = ServiceRequest(
        request_number=request_number,
        status="New",
        **data,
    )
    db.add(sr)
    await db.flush()
    await db.refresh(sr)
    await audit_service.record_audit_log(
        db,
        action="CREATE",
        resource_type="ServiceRequest",
        resource_id=str(sr.request_id),
        new_values={"request_number": request_number, "status": "New"},
    )
    logger.info("service_request_created", request_number=request_number)
    return sr


async def get_service_requests(
    db: AsyncSession,
    status: str | None,
    skip: int,
    limit: int,
) -> tuple[list[ServiceRequest], int]:
    """サービスリクエスト一覧をページネーション付きで取得"""
    query = select(ServiceRequest)
    if status:
        query = query.where(ServiceRequest.status == status)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset(skip).limit(limit).order_by(ServiceRequest.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    return list(items), total


async def get_service_request(db: AsyncSession, request_id: uuid.UUID) -> ServiceRequest | None:
    """IDでサービスリクエストを取得"""
    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.request_id == request_id)
    )
    return result.scalar_one_or_none()


async def update_service_request(
    db: AsyncSession, request_id: uuid.UUID, data: dict[str, Any]
) -> ServiceRequest | None:
    """サービスリクエストを更新する"""
    sr = await get_service_request(db, request_id)
    if not sr:
        return None

    old_values = {k: str(getattr(sr, k)) for k in data if hasattr(sr, k)}
    for field, value in data.items():
        setattr(sr, field, value)
    await db.flush()
    await db.refresh(sr)
    await audit_service.record_audit_log(
        db,
        action="UPDATE",
        resource_type="ServiceRequest",
        resource_id=str(sr.request_id),
        old_values=old_values,
        new_values=data,
    )
    return sr


async def transition_service_request_status(
    db: AsyncSession,
    request_id: uuid.UUID,
    target_status: str,
    comment: str | None,
) -> ServiceRequest:
    """サービスリクエストのステータスを遷移させる"""
    sr = await get_service_request(db, request_id)
    if not sr:
        raise ValueError(f"サービスリクエスト '{request_id}' が見つかりません。")

    allowed = VALID_SR_TRANSITIONS.get(sr.status, set())
    if target_status not in allowed:
        raise ValueError(
            f"ステータス '{sr.status}' から '{target_status}' への遷移は許可されていません。"
            f"許可される遷移: {', '.join(allowed) or 'なし'}"
        )

    old_status = sr.status
    sr.status = target_status

    if target_status == "Fulfilled":
        sr.fulfilled_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(sr)
    await audit_service.record_audit_log(
        db,
        action="STATUS_TRANSITION",
        resource_type="ServiceRequest",
        resource_id=str(sr.request_id),
        old_values={"status": old_status},
        new_values={"status": target_status, "comment": comment},
    )
    return sr
