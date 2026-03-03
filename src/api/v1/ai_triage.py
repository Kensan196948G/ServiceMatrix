"""AIトリアージAPI - 手動トリアージ・バッチ処理・プロバイダー情報"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.user import User, UserRole
from src.schemas.ai_triage import (
    BatchTriageItem,
    BatchTriageRequest,
    BatchTriageResponse,
    IncidentTriageRequest,
    ProviderInfoResponse,
    TriageRequest,
    TriageResponse,
)
from src.services.ai_triage_service import ai_triage_service

router = APIRouter(prefix="/ai-triage", tags=["ai-triage"])


@router.post(
    "/analyze",
    response_model=TriageResponse,
    summary="手動トリアージ実行",
    description="タイトルと説明からAI優先度・カテゴリを判定します。",
)
async def analyze_text(
    data: TriageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """テキストベースの手動トリアージ"""
    result = await ai_triage_service.triage(data.title, data.description)
    return TriageResponse(
        priority=result.priority,
        category=result.category,
        confidence=result.confidence,
        reasoning=result.reasoning,
        provider=result.provider,
    )


@router.post(
    "/incident",
    response_model=TriageResponse,
    summary="インシデントトリアージ実行",
    description="既存インシデントに対してAIトリアージを実行し結果を保存します。",
)
async def triage_incident(
    data: IncidentTriageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
):
    """既存インシデントのトリアージ実行"""
    result = await ai_triage_service.apply_triage_to_incident(db, str(data.incident_id))
    if result.priority == "Unknown" and result.confidence == 0.0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="インシデントが見つかりません",
        )
    return TriageResponse(
        priority=result.priority,
        category=result.category,
        confidence=result.confidence,
        reasoning=result.reasoning,
        provider=result.provider,
    )


@router.post(
    "/batch",
    response_model=BatchTriageResponse,
    summary="バッチトリアージ実行",
    description="複数インシデントを一括でAIトリアージします。",
)
async def batch_triage(
    data: BatchTriageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
            )
        ),
    ],
):
    """バッチトリアージ実行"""
    results = await ai_triage_service.batch_triage(db, [str(iid) for iid in data.incident_ids])
    items = [BatchTriageItem(**r) for r in results]
    success_count = sum(1 for r in results if r["success"])
    return BatchTriageResponse(
        items=items,
        total=len(items),
        success_count=success_count,
        failure_count=len(items) - success_count,
    )


@router.get(
    "/provider",
    response_model=ProviderInfoResponse,
    summary="プロバイダー情報取得",
    description="現在使用中のAIトリアージプロバイダー情報を返します。",
)
async def get_provider_info(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """プロバイダー情報取得"""
    info = ai_triage_service.get_provider_info()
    return ProviderInfoResponse(**info)
