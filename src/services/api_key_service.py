"""APIキー管理サービス"""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import APIKey


def generate_api_key() -> str:
    """ランダムな32文字のAPIキーを生成する"""
    return secrets.token_hex(16)


async def create_api_key(
    db: AsyncSession,
    name: str,
    owner_id: str | None = None,
    rate_limit: int = 1000,
) -> tuple[APIKey, str]:
    """APIキーを作成し、(モデル, 生キー)のタプルを返す"""
    raw_key = generate_api_key()
    key_hash = APIKey.hash_key(raw_key)
    key_prefix = raw_key[:8]

    api_key = APIKey(
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=name,
        owner_id=owner_id,
        rate_limit=rate_limit,
    )
    db.add(api_key)
    await db.flush()
    return api_key, raw_key


async def get_api_key(db: AsyncSession, key_id: str) -> APIKey | None:
    """IDでAPIキーを取得する"""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    return result.scalar_one_or_none()


async def validate_api_key(db: AsyncSession, raw_key: str) -> APIKey | None:
    """生キーを検証し、有効なAPIKeyモデルを返す"""
    key_hash = APIKey.hash_key(raw_key)
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def list_api_keys(db: AsyncSession, owner_id: str | None = None) -> list[APIKey]:
    """APIキー一覧を取得する"""
    stmt = select(APIKey)
    if owner_id is not None:
        stmt = stmt.where(APIKey.owner_id == owner_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: str) -> bool:
    """APIキーを無効化する"""
    api_key = await get_api_key(db, key_id)
    if api_key is None:
        return False
    api_key.is_active = False
    await db.flush()
    return True
