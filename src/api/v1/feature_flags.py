"""Feature Flag REST API - Issue #91, Phase 9-DEPLOY-2"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import get_redis
from src.core.database import get_db
from src.middleware.rbac import require_role
from src.models.user import User, UserRole
from src.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagEvaluation,
    FeatureFlagResponse,
    FeatureFlagUpdate,
)
from src.services.feature_flag_service import FeatureFlagService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])

# 書き込み権限を持つロール
_WRITE_ROLES = (UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER)


def _get_service(db: AsyncSession) -> FeatureFlagService:
    """FeatureFlagService インスタンスを生成する（Redis はベストエフォート）。"""
    try:
        redis_client = get_redis()
    except Exception:
        redis_client = None
    return FeatureFlagService(db, redis_client)


# ── 一覧取得 ──────────────────────────────────────────────────────────────────


@router.get("", response_model=list[FeatureFlagResponse])
async def list_feature_flags(
    enabled_only: bool = Query(False, description="有効フラグのみ取得"),
    tenant_id: uuid.UUID | None = Query(None, description="テナントIDでフィルタ"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.VIEWER)),
) -> list[FeatureFlagResponse]:
    """Feature Flag の一覧を取得する。"""
    svc = _get_service(db)
    flags = await svc.list_all(enabled_only=enabled_only, tenant_id=tenant_id)
    return [FeatureFlagResponse.model_validate(f) for f in flags]


# ── 作成 ─────────────────────────────────────────────────────────────────────


@router.post("", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    payload: FeatureFlagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_WRITE_ROLES)),
) -> FeatureFlagResponse:
    """Feature Flag を作成する（Admin/Manager 専用）。"""
    svc = _get_service(db)
    # 重複チェック
    existing = await svc.get_by_name(payload.name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Feature flag '{payload.name}' already exists",
        )
    flag = await svc.create(payload, updated_by=str(current_user.user_id))
    return FeatureFlagResponse.model_validate(flag)


# ── 取得（名前） ──────────────────────────────────────────────────────────────


@router.get("/{name}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.VIEWER)),
) -> FeatureFlagResponse:
    """Feature Flag を名前で取得する。"""
    svc = _get_service(db)
    flag = await svc.get_by_name(name)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found",
        )
    return FeatureFlagResponse.model_validate(flag)


# ── 更新 ─────────────────────────────────────────────────────────────────────


@router.put("/{name}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    name: str,
    payload: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_WRITE_ROLES)),
) -> FeatureFlagResponse:
    """Feature Flag を更新する（Admin/Manager 専用）。"""
    svc = _get_service(db)
    flag = await svc.get_by_name(name)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found",
        )
    updated = await svc.update(flag, payload, updated_by=str(current_user.user_id))
    return FeatureFlagResponse.model_validate(updated)


# ── 削除 ─────────────────────────────────────────────────────────────────────


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_feature_flag(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_WRITE_ROLES)),
) -> None:
    """Feature Flag を削除する（Admin/Manager 専用）。"""
    svc = _get_service(db)
    flag = await svc.get_by_name(name)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found",
        )
    await svc.delete(flag)


# ── トグル ────────────────────────────────────────────────────────────────────


@router.post("/{name}/toggle", response_model=FeatureFlagResponse)
async def toggle_feature_flag(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_WRITE_ROLES)),
) -> FeatureFlagResponse:
    """Feature Flag の有効/無効を切り替える（Admin/Manager 専用）。"""
    svc = _get_service(db)
    flag = await svc.get_by_name(name)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found",
        )
    toggled = await svc.toggle(flag, updated_by=str(current_user.user_id))
    return FeatureFlagResponse.model_validate(toggled)


# ── 評価 ─────────────────────────────────────────────────────────────────────


@router.get("/{name}/evaluate", response_model=FeatureFlagEvaluation)
async def evaluate_feature_flag(
    name: str,
    user_id: str | None = Query(None, description="カナリア判定に使用するユーザーID"),
    tenant_id: str | None = Query(None, description="テナントID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.VIEWER)),
) -> Any:
    """Feature Flag を評価する（有効/無効と理由を返す）。"""
    svc = _get_service(db)
    flag = await svc.get_by_name(name)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found",
        )
    return svc.evaluate(flag, user_id=user_id, tenant_id=tenant_id)
