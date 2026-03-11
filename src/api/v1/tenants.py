"""テナント管理 API - Issue #75 マルチテナント基盤"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import require_role
from src.models.tenant import TenantPlan
from src.models.user import User, UserRole
from src.services.tenant_service import tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str = Field(default=TenantPlan.FREE)
    settings: dict[str, Any] | None = None


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    plan: str | None = None
    is_active: bool | None = None
    settings: dict[str, Any] | None = None


class TenantResponse(BaseModel):
    tenant_id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    settings: dict[str, Any]

    model_config = {"from_attributes": True}


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> TenantResponse:
    """テナントを作成する（SystemAdmin 専用）。"""
    existing = await tenant_service.get_tenant_by_slug(db, payload.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{payload.slug}' already exists",
        )
    tenant = await tenant_service.create_tenant(
        db,
        name=payload.name,
        slug=payload.slug,
        plan=payload.plan,
        settings=payload.settings,
    )
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        settings=tenant_service.get_tenant_settings(tenant),
    )


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> list[TenantResponse]:
    """テナント一覧を取得する（SystemAdmin 専用）。"""
    tenants = await tenant_service.list_tenants(db, skip=skip, limit=limit)
    return [
        TenantResponse(
            tenant_id=t.tenant_id,
            name=t.name,
            slug=t.slug,
            plan=t.plan,
            is_active=t.is_active,
            settings=tenant_service.get_tenant_settings(t),
        )
        for t in tenants
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> TenantResponse:
    """テナントを取得する（SystemAdmin 専用）。"""
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        settings=tenant_service.get_tenant_settings(tenant),
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> TenantResponse:
    """テナントを更新する（SystemAdmin 専用）。"""
    tenant = await tenant_service.update_tenant(
        db,
        tenant_id=tenant_id,
        name=payload.name,
        plan=payload.plan,
        is_active=payload.is_active,
        settings=payload.settings,
    )
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        settings=tenant_service.get_tenant_settings(tenant),
    )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> None:
    """テナントを削除する（SystemAdmin 専用）。"""
    deleted = await tenant_service.delete_tenant(db, tenant_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
