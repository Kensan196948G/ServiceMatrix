"""CMDB構成管理サービス"""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.cmdb import CIRelationship, ConfigurationItem
from src.services import audit_service

logger = get_logger(__name__)


async def create_ci(db: AsyncSession, data: dict[str, Any]) -> ConfigurationItem:
    ci = ConfigurationItem(**data)
    db.add(ci)
    await db.flush()
    await db.refresh(ci)
    await audit_service.record_audit_log(
        db,
        action="CI_CREATE",
        resource_type="ConfigurationItem",
        resource_id=str(ci.ci_id),
        new_values={"ci_name": ci.ci_name, "ci_type": ci.ci_type},
    )
    logger.info("ci_created", ci_id=str(ci.ci_id), ci_name=ci.ci_name)
    return ci


async def get_cis(
    db: AsyncSession,
    ci_type: str | None,
    status: str | None,
    skip: int,
    limit: int,
    department: str | None = None,
) -> tuple[list[ConfigurationItem], int]:
    query = select(ConfigurationItem)
    if ci_type:
        query = query.where(ConfigurationItem.ci_type == ci_type)
    if status:
        query = query.where(ConfigurationItem.status == status)
    if department:
        query = query.where(ConfigurationItem.department == department)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset(skip).limit(limit).order_by(ConfigurationItem.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_ci(db: AsyncSession, ci_id: uuid.UUID) -> ConfigurationItem | None:
    result = await db.execute(select(ConfigurationItem).where(ConfigurationItem.ci_id == ci_id))
    return result.scalar_one_or_none()


async def update_ci(
    db: AsyncSession, ci_id: uuid.UUID, data: dict[str, Any]
) -> ConfigurationItem | None:
    ci = await get_ci(db, ci_id)
    if not ci:
        return None

    old_values = {k: getattr(ci, k) for k in data}
    for field, value in data.items():
        setattr(ci, field, value)
    await db.flush()
    await db.refresh(ci)
    await audit_service.record_audit_log(
        db,
        action="CI_UPDATE",
        resource_type="ConfigurationItem",
        resource_id=str(ci.ci_id),
        old_values={k: str(v) for k, v in old_values.items()},
        new_values={k: str(v) for k, v in data.items()},
    )
    return ci


async def create_ci_relationship(db: AsyncSession, data: dict[str, Any]) -> CIRelationship:
    if data.get("source_ci_id") == data.get("target_ci_id"):
        raise ValueError("source_ci_id と target_ci_id に同じCIは指定できません")

    rel = CIRelationship(**data)
    db.add(rel)
    await db.flush()
    await db.refresh(rel)
    logger.info(
        "ci_relationship_created",
        relationship_id=str(rel.relationship_id),
        relationship_type=rel.relationship_type,
    )
    return rel


async def get_ci_relationships(db: AsyncSession, ci_id: uuid.UUID) -> list[CIRelationship]:
    result = await db.execute(
        select(CIRelationship).where(
            or_(
                CIRelationship.source_ci_id == ci_id,
                CIRelationship.target_ci_id == ci_id,
            )
        )
    )
    return list(result.scalars().all())


async def analyze_impact(db: AsyncSession, ci_id: uuid.UUID) -> dict:
    result = await db.execute(select(CIRelationship).where(CIRelationship.source_ci_id == ci_id))
    outgoing = list(result.scalars().all())

    direct_target_ids = [r.target_ci_id for r in outgoing]
    direct_dependents: list[ConfigurationItem] = []
    for tid in direct_target_ids:
        ci = await get_ci(db, tid)
        if ci:
            direct_dependents.append(ci)

    visited: set[uuid.UUID] = set(direct_target_ids)
    queue = list(direct_target_ids)
    while queue:
        current_id = queue.pop(0)
        sub_result = await db.execute(
            select(CIRelationship).where(CIRelationship.source_ci_id == current_id)
        )
        for rel in sub_result.scalars().all():
            if rel.target_ci_id not in visited:
                visited.add(rel.target_ci_id)
                queue.append(rel.target_ci_id)

    ci = await get_ci(db, ci_id)
    return {
        "ci_id": ci_id,
        "ci_name": ci.ci_name if ci else "",
        "direct_dependents": direct_dependents,
        "transitive_count": len(visited),
    }
