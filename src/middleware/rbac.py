"""RBAC（ロールベースアクセス制御）ミドルウェア - 6ロール定義"""
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.cache import is_token_blacklisted
from src.core.database import get_db
from src.core.security import decode_token
from src.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ロール階層（上位ロールは下位ロールの権限を包含）
ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.SYSTEM_ADMIN: 100,
    UserRole.SERVICE_MANAGER: 80,
    UserRole.CHANGE_MANAGER: 60,
    UserRole.INCIDENT_MANAGER: 50,
    UserRole.OPERATOR: 30,
    UserRole.AI_AGENT: 20,
    UserRole.VIEWER: 10,
}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """JWTトークンからカレントユーザーを取得"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except ValueError:
        raise credentials_exception

    if await is_token_blacklisted(token):
        raise credentials_exception

    result = await db.execute(select(User).where(User.user_id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*allowed_roles: UserRole):
    """指定ロール以上の権限を要求するデペンデンシー"""
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = min(ROLE_HIERARCHY.get(role, 0) for role in allowed_roles)
        if user_level < required_level and current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"この操作には {', '.join(r.value for r in allowed_roles)} 以上のロールが必要です",
            )
        return current_user
    return role_checker
