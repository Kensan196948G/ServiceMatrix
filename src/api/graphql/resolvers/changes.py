"""変更管理 GraphQL リゾルバー"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.graphql.types.change import ChangeType
from src.models.change import Change


def _to_gql(row: Change) -> ChangeType:
    return ChangeType(
        id=row.change_id,
        change_number=row.change_number,
        title=row.title,
        description=row.description,
        change_type=row.change_type,
        status=row.status,
        requested_by=row.requested_by,
        assigned_to=row.assigned_to,
        risk_score=row.risk_score,
        risk_level=row.risk_level,
        scheduled_start_at=row.scheduled_start_at,
        scheduled_end_at=row.scheduled_end_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def resolve_changes(
    session: AsyncSession,
    status: str | None = None,
    change_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[ChangeType]:
    """変更一覧を取得（フィルタ・ページネーション対応）"""
    stmt = select(Change).order_by(Change.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Change.status == status)
    if change_type:
        stmt = stmt.where(Change.change_type == change_type)
    result = await session.execute(stmt)
    return [_to_gql(row) for row in result.scalars().all()]


async def resolve_change(session: AsyncSession, id: UUID) -> ChangeType | None:
    """変更単件取得"""
    result = await session.execute(select(Change).where(Change.change_id == id))
    row = result.scalar_one_or_none()
    return _to_gql(row) if row else None
