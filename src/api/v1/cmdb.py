"""CMDB構成管理API"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.user import User
from src.schemas.cmdb import (
    BatchImpactRequest,
    BatchImpactResponse,
    CICreate,
    CIRelationshipCreate,
    CIRelationshipResponse,
    CIResponse,
    CIUpdate,
    GraphResponse,
    ImpactAnalysisResponse,
)
from src.services import cmdb_service

router = APIRouter(prefix="/cmdb", tags=["cmdb"])


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    ci_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
):
    """全CIと関係をグラフ構造で取得"""
    return await cmdb_service.get_graph(db, ci_type=ci_type, status=status_filter)


@router.get("/cis", response_model=list[CIResponse])
async def list_cis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    ci_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    items, _ = await cmdb_service.get_cis(db, ci_type, status_filter, skip, limit)
    return items


@router.post("/cis", response_model=CIResponse, status_code=status.HTTP_201_CREATED)
async def create_ci(
    data: CICreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.create_ci(db, data.model_dump(exclude_none=True))
    return ci


@router.get("/cis/{ci_id}", response_model=CIResponse)
async def get_ci(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.get_ci(db, ci_id)
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return ci


@router.patch("/cis/{ci_id}", response_model=CIResponse)
async def update_ci(
    ci_id: uuid.UUID,
    data: CIUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.update_ci(db, ci_id, data.model_dump(exclude_none=True))
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return ci


@router.get("/cis/{ci_id}/graph", response_model=GraphResponse)
async def get_ci_graph(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    depth: int = Query(default=3, ge=1, le=5),
):
    """特定CIを起点とした依存グラフをdepth階層まで展開"""
    ci = await cmdb_service.get_ci(db, ci_id)
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return await cmdb_service.get_ci_graph(db, ci_id, depth=depth)


@router.get("/cis/{ci_id}/upstream", response_model=list[CIResponse])
async def get_upstream_cis(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """このCIに依存している上流CIを取得"""
    ci = await cmdb_service.get_ci(db, ci_id)
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return await cmdb_service.get_upstream_cis(db, ci_id)


@router.get("/cis/{ci_id}/relationships", response_model=list[CIRelationshipResponse])
async def get_ci_relationships(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return await cmdb_service.get_ci_relationships(db, ci_id)


@router.post(
    "/relationships",
    response_model=CIRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ci_relationship(
    data: CIRelationshipCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        rel = await cmdb_service.create_ci_relationship(db, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return rel


@router.get("/cis/{ci_id}/impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.get_ci(db, ci_id)
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return await cmdb_service.analyze_impact(db, ci_id)


@router.post("/batch-impact", response_model=BatchImpactResponse)
async def batch_impact(
    data: BatchImpactRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """複数CIの影響分析を一括実行"""
    return await cmdb_service.batch_impact_analysis(db, data.ci_ids)
