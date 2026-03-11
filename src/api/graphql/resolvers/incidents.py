"""インシデント GraphQL リゾルバー"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.graphql.types.incident import IncidentType
from src.models.incident import Incident


def _to_gql(row: Incident) -> IncidentType:
    return IncidentType(
        id=row.incident_id,
        incident_number=row.incident_number,
        title=row.title,
        description=row.description,
        priority=row.priority,
        status=row.status,
        reported_by=row.reported_by,
        assigned_to=row.assigned_to,
        sla_response_due_at=row.sla_response_due_at,
        sla_resolution_due_at=row.sla_resolution_due_at,
        sla_breached=row.sla_breached,
        resolved_at=row.resolved_at,
        closed_at=row.closed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def resolve_incidents(
    session: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[IncidentType]:
    """インシデント一覧を取得（フィルタ・ページネーション対応）"""
    stmt = select(Incident).order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Incident.status == status)
    if priority:
        stmt = stmt.where(Incident.priority == priority)
    result = await session.execute(stmt)
    return [_to_gql(row) for row in result.scalars().all()]


async def resolve_incident(session: AsyncSession, id: UUID) -> IncidentType | None:
    """インシデント単件取得"""
    result = await session.execute(
        select(Incident).where(Incident.incident_id == id)
    )
    row = result.scalar_one_or_none()
    return _to_gql(row) if row else None
