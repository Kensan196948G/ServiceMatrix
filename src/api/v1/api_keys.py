"""APIキー管理エンドポイント"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.user import User
from src.schemas.api_key import APIKeyCreate, APIKeyCreateResponse, APIKeyResponse
from src.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="APIキー作成",
    description="新しいAPIキーを作成します。生キーは一度のみ表示されます。",
)
async def create_api_key(
    body: APIKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    api_key, raw_key = await api_key_service.create_api_key(
        db=db,
        name=body.name,
        owner_id=str(current_user.user_id),
        rate_limit=body.rate_limit,
    )
    return APIKeyCreateResponse(
        id=str(api_key.id),
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        raw_key=raw_key,
        rate_limit=api_key.rate_limit,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )


@router.get(
    "",
    response_model=list[APIKeyResponse],
    summary="APIキー一覧",
    description="自分が所有するAPIキーの一覧を取得します。",
)
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    keys = await api_key_service.list_api_keys(db, owner_id=str(current_user.user_id))
    return [
        APIKeyResponse(
            id=str(k.id),
            key_prefix=k.key_prefix,
            name=k.name,
            owner_id=k.owner_id,
            rate_limit=k.rate_limit,
            is_active=k.is_active,
            expires_at=k.expires_at,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="APIキー無効化",
    description="指定したAPIキーを無効化します。",
)
async def revoke_api_key(
    key_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    success = await api_key_service.revoke_api_key(db, key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="APIキーが見つかりません",
        )
    return None
