"""認証API - /auth/login, /auth/refresh, /auth/me, /auth/users"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.rate_limit import limiter
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from src.middleware.rbac import get_current_user, require_role
from src.models.user import User, UserRole
from src.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """ユーザーログイン - JWT発行"""
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効化されています",
        )

    token_data = {"sub": str(user.user_id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # 最終ログイン時刻を更新
    user.last_login_at = datetime.now(UTC)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """リフレッシュトークンによるアクセストークン再発行"""
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        user_id = payload.get("sub")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが無効です",
        ) from e

    result = await db.execute(select(User).where(User.user_id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="ユーザーが存在しません"
        )

    token_data = {"sub": str(user.user_id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """カレントユーザー情報取得"""
    return current_user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[
        User, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """ユーザー一覧取得（管理者のみ）"""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """ユーザー作成（システム管理者のみ）"""
    # 重複チェック
    dup = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="ユーザー名またはメールアドレスがすでに使用されています"
        )

    try:
        role_enum = UserRole(body.role)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"無効なロール: {body.role}") from err

    user = User(
        user_id=uuid.uuid4(),
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        role=role_enum,
        is_active=body.is_active,
    )
    db.add(user)
    await db.flush()
    return user
