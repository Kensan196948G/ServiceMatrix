"""サービスカタログAPI"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.service_catalog import ServiceCatalog
from src.models.user import User, UserRole
from src.schemas.service_catalog import (
    ServiceCatalogCreate,
    ServiceCatalogResponse,
    ServiceCatalogUpdate,
)
from src.schemas.service_request import ServiceRequestResponse
from src.services import service_request_service

router = APIRouter(prefix="/service-catalog", tags=["service-catalog"])


@router.get("", response_model=list[ServiceCatalogResponse])
async def list_service_catalog(
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(default=True),
):
    """サービスカタログ一覧取得（認証不要）"""
    stmt = select(ServiceCatalog).order_by(ServiceCatalog.name)
    if active_only:
        stmt = stmt.where(ServiceCatalog.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{catalog_id}", response_model=ServiceCatalogResponse)
async def get_service_catalog(
    catalog_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """サービスカタログ詳細取得"""
    result = await db.execute(
        select(ServiceCatalog).where(ServiceCatalog.catalog_id == catalog_id)
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="カタログが見つかりません"
        )
    return catalog


@router.post("", response_model=ServiceCatalogResponse, status_code=status.HTTP_201_CREATED)
async def create_service_catalog(
    data: ServiceCatalogCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
):
    """サービスカタログ作成（SYSTEM_ADMINのみ）"""
    catalog = ServiceCatalog(catalog_id=uuid.uuid4(), **data.model_dump())
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


@router.patch("/{catalog_id}", response_model=ServiceCatalogResponse)
async def update_service_catalog(
    catalog_id: uuid.UUID,
    data: ServiceCatalogUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
):
    """サービスカタログ更新（SYSTEM_ADMINのみ）"""
    result = await db.execute(
        select(ServiceCatalog).where(ServiceCatalog.catalog_id == catalog_id)
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="カタログが見つかりません"
        )
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(catalog, key, value)
    await db.flush()
    await db.refresh(catalog)
    return catalog


@router.delete("/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_catalog(
    catalog_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
):
    """サービスカタログ削除（SYSTEM_ADMINのみ）"""
    result = await db.execute(
        select(ServiceCatalog).where(ServiceCatalog.catalog_id == catalog_id)
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="カタログが見つかりません"
        )
    await db.delete(catalog)


@router.post(
    "/{catalog_id}/request",
    response_model=ServiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_from_catalog(
    catalog_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """カタログからサービスリクエスト作成"""
    result = await db.execute(
        select(ServiceCatalog).where(
            ServiceCatalog.catalog_id == catalog_id, ServiceCatalog.is_active.is_(True)
        )
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="カタログが見つかりません"
        )

    sr = await service_request_service.create_service_request(
        db,
        {
            "title": catalog.name,
            "description": catalog.description,
            "request_type": catalog.category,
            "catalog_id": catalog_id,
            "requested_by": current_user.user_id,
        },
    )
    return sr
