"""CMDB GraphQL リゾルバー"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.graphql.types.cmdb import CmdbItemType
from src.models.cmdb import ConfigurationItem


def _to_gql(row: ConfigurationItem) -> CmdbItemType:
    return CmdbItemType(
        id=row.ci_id,
        ci_number=str(row.ci_id),  # CIにci_numberがないためUUIDを代替使用
        name=row.ci_name,
        ci_type=row.ci_type,
        ci_class=row.ci_class,
        status=row.status,
        owner_id=row.owner_id,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def resolve_cmdb_items(
    session: AsyncSession,
    ci_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[CmdbItemType]:
    """CI一覧を取得（フィルタ・ページネーション対応）"""
    stmt = (
        select(ConfigurationItem)
        .order_by(ConfigurationItem.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if ci_type:
        stmt = stmt.where(ConfigurationItem.ci_type == ci_type)
    if status:
        stmt = stmt.where(ConfigurationItem.status == status)
    result = await session.execute(stmt)
    return [_to_gql(row) for row in result.scalars().all()]


async def resolve_cmdb_item(session: AsyncSession, id: UUID) -> CmdbItemType | None:
    """CI単件取得"""
    result = await session.execute(
        select(ConfigurationItem).where(ConfigurationItem.ci_id == id)
    )
    row = result.scalar_one_or_none()
    return _to_gql(row) if row else None
