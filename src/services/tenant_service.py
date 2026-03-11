"""テナントサービス - Issue #75 マルチテナント基盤"""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tenant import Tenant, TenantPlan


class TenantService:
    """テナント CRUD・プラン管理サービス。"""

    async def create_tenant(
        self,
        db: AsyncSession,
        name: str,
        slug: str,
        plan: str = TenantPlan.FREE,
        settings: dict[str, Any] | None = None,
    ) -> Tenant:
        """テナントを作成する。"""
        tenant = Tenant(
            tenant_id=uuid.uuid4(),
            name=name,
            slug=slug,
            plan=plan,
            is_active=True,
            settings_json=json.dumps(settings) if settings else None,
        )
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant

    async def get_tenant(self, db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
        """ID でテナントを取得する。"""
        result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, db: AsyncSession, slug: str) -> Tenant | None:
        """slug でテナントを取得する。"""
        result = await db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def list_tenants(self, db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Tenant]:
        """テナント一覧を取得する。"""
        result = await db.execute(select(Tenant).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_tenant(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        name: str | None = None,
        plan: str | None = None,
        is_active: bool | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Tenant | None:
        """テナントを更新する。"""
        tenant = await self.get_tenant(db, tenant_id)
        if tenant is None:
            return None
        if name is not None:
            tenant.name = name
        if plan is not None:
            tenant.plan = plan
        if is_active is not None:
            tenant.is_active = is_active
        if settings is not None:
            tenant.settings_json = json.dumps(settings)
        await db.flush()
        await db.refresh(tenant)
        return tenant

    async def delete_tenant(self, db: AsyncSession, tenant_id: uuid.UUID) -> bool:
        """テナントを削除する。存在しない場合は False を返す。"""
        tenant = await self.get_tenant(db, tenant_id)
        if tenant is None:
            return False
        await db.delete(tenant)
        await db.flush()
        return True

    def get_tenant_settings(self, tenant: Tenant) -> dict[str, Any]:
        """テナントの設定 JSON をデシリアライズして返す。"""
        if tenant.settings_json:
            return json.loads(tenant.settings_json)
        return {}

    def is_plan_allowed(self, tenant: Tenant, required_plan: TenantPlan) -> bool:
        """テナントのプランが要求プラン以上かを確認する。"""
        plan_order = {
            TenantPlan.FREE: 0,
            TenantPlan.STANDARD: 1,
            TenantPlan.ENTERPRISE: 2,
        }
        current = plan_order.get(TenantPlan(tenant.plan), -1)
        required = plan_order.get(required_plan, 999)
        return current >= required


tenant_service = TenantService()
