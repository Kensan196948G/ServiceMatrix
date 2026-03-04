"""テナント管理API - CRUD"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import require_role
from src.models.user import User, UserRole
from src.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from src.services import tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="テナント作成",
    description="新規テナントを作成します。slugはユニークである必要があります。",
)
async def create_tenant(
    data: TenantCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN)),
    ],
):
    """テナント作成"""
    existing = await tenant_service.get_tenant_by_slug(db, data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"スラッグ '{data.slug}' は既に使用されています",
        )
    return await tenant_service.create_tenant(db, data.model_dump())


@router.get(
    "",
    response_model=list[TenantResponse],
    summary="テナント一覧取得",
    description="テナント一覧をページネーション付きで返します。",
)
async def list_tenants(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN)),
    ],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """テナント一覧取得"""
    return await tenant_service.list_tenants(db, limit=limit, offset=offset)


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="テナント詳細取得",
    description="指定されたIDのテナント詳細を返します。",
)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN)),
    ],
):
    """テナント詳細取得"""
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="テナントが見つかりません",
        )
    return tenant


@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="テナント更新",
    description="指定されたIDのテナントを更新します。",
)
async def update_tenant(
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN)),
    ],
):
    """テナント更新"""
    if data.slug:
        existing = await tenant_service.get_tenant_by_slug(db, data.slug)
        if existing and str(existing.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"スラッグ '{data.slug}' は既に使用されています",
            )
    tenant = await tenant_service.update_tenant(
        db, tenant_id, data.model_dump(exclude_none=True)
    )
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="テナントが見つかりません",
        )
    return tenant


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="テナント削除",
    description="指定されたIDのテナントを削除します。",
)
async def delete_tenant(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN)),
    ],
):
    """テナント削除"""
    deleted = await tenant_service.delete_tenant(db, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="テナントが見つかりません",
        )
