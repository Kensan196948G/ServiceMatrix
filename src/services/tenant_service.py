"""テナント管理ビジネスロジック - CRUD操作"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.tenant import Tenant

logger = get_logger(__name__)


async def create_tenant(db: AsyncSession, data: dict[str, Any]) -> Tenant:
    """テナントを作成する"""
    tenant = Tenant(**data)
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    logger.info("tenant_created", tenant_slug=tenant.slug)
    return tenant


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    """テナントIDで取得する"""
    result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
    return result.scalar_one_or_none()


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    """スラッグでテナントを取得する"""
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none()


async def list_tenants(
    db: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Tenant]:
    """テナント一覧を取得する"""
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def update_tenant(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict[str, Any]
) -> Tenant | None:
    """テナントを更新する"""
    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        return None
    for field, value in data.items():
        setattr(tenant, field, value)
    await db.flush()
    await db.refresh(tenant)
    logger.info("tenant_updated", tenant_slug=tenant.slug)
    return tenant


async def delete_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    """テナントを削除する"""
    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        return False
    await db.delete(tenant)
    await db.flush()
    logger.info("tenant_deleted", tenant_id=str(tenant_id))
    return True
