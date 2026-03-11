"""Feature Flag サービス - Issue #90, Phase 9-DEPLOY-1

実装方針:
- SQLAlchemy で DB 永続化
- Redis キャッシュ（TTL: 60秒）で高速評価
- ユーザーIDのハッシュベース一貫ロールアウト
- テナント限定フラグ対応
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select

from src.models.feature_flag import FeatureFlag
from src.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagEvaluation,
    FeatureFlagUpdate,
)

if TYPE_CHECKING:
    import redis.asyncio as aioredis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Redis キャッシュ TTL（秒）
FLAG_CACHE_TTL = 60
FLAG_CACHE_PREFIX = "feature_flag"


class FeatureFlagService:
    """Feature Flag の CRUD・評価サービス。"""

    def __init__(
        self,
        db: AsyncSession,
        redis_client: aioredis.Redis | None = None,
    ) -> None:
        self._db = db
        self._redis = redis_client

    # ── キャッシュ操作 ───────────────────────────────────────────────────────

    def _cache_key(self, name: str) -> str:
        return f"{FLAG_CACHE_PREFIX}:{name}"

    async def _get_from_cache(self, name: str) -> dict[str, Any] | None:
        if self._redis is None:
            return None
        raw = await self._redis.get(self._cache_key(name))
        if raw:
            return json.loads(raw)
        return None

    async def _set_cache(self, flag: FeatureFlag) -> None:
        if self._redis is None:
            return
        data = {
            "is_enabled": flag.is_enabled,
            "rollout_percentage": flag.rollout_percentage,
            "tenant_id": str(flag.tenant_id) if flag.tenant_id else None,
        }
        await self._redis.setex(
            self._cache_key(flag.name),
            FLAG_CACHE_TTL,
            json.dumps(data),
        )

    async def _invalidate_cache(self, name: str) -> None:
        if self._redis is None:
            return
        await self._redis.delete(self._cache_key(name))

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        data: FeatureFlagCreate,
        updated_by: str | None = None,
    ) -> FeatureFlag:
        """Feature Flag を新規作成する。"""
        flag = FeatureFlag(
            name=data.name,
            description=data.description,
            is_enabled=data.is_enabled,
            rollout_percentage=data.rollout_percentage,
            tenant_id=data.tenant_id,
            metadata_json=data.metadata_json,
            updated_by=updated_by,
        )
        self._db.add(flag)
        await self._db.commit()
        await self._db.refresh(flag)
        await self._set_cache(flag)
        logger.info("feature_flag_created", name=flag.name, enabled=flag.is_enabled)
        return flag

    async def get_by_name(self, name: str) -> FeatureFlag | None:
        """フラグ名で取得する。"""
        result = await self._db.execute(
            select(FeatureFlag).where(FeatureFlag.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, flag_id: uuid.UUID) -> FeatureFlag | None:
        """フラグIDで取得する。"""
        result = await self._db.execute(
            select(FeatureFlag).where(FeatureFlag.flag_id == flag_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        enabled_only: bool = False,
        tenant_id: uuid.UUID | None = None,
    ) -> list[FeatureFlag]:
        """全フラグを一覧取得する。"""
        stmt = select(FeatureFlag)
        if enabled_only:
            stmt = stmt.where(FeatureFlag.is_enabled == True)  # noqa: E712
        if tenant_id is not None:
            stmt = stmt.where(
                (FeatureFlag.tenant_id == tenant_id)
                | (FeatureFlag.tenant_id == None)  # noqa: E711
            )
        stmt = stmt.order_by(FeatureFlag.name)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        flag: FeatureFlag,
        data: FeatureFlagUpdate,
        updated_by: str | None = None,
    ) -> FeatureFlag:
        """Feature Flag を更新する。"""
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(flag, field, value)
        if updated_by:
            flag.updated_by = updated_by
        await self._db.commit()
        await self._db.refresh(flag)
        await self._invalidate_cache(flag.name)
        await self._set_cache(flag)
        logger.info("feature_flag_updated", name=flag.name)
        return flag

    async def delete(self, flag: FeatureFlag) -> None:
        """Feature Flag を削除する。"""
        name = flag.name
        await self._db.delete(flag)
        await self._db.commit()
        await self._invalidate_cache(name)
        logger.info("feature_flag_deleted", name=name)

    async def toggle(self, flag: FeatureFlag, updated_by: str | None = None) -> FeatureFlag:
        """有効/無効を切り替える。"""
        flag.is_enabled = not flag.is_enabled
        if updated_by:
            flag.updated_by = updated_by
        await self._db.commit()
        await self._db.refresh(flag)
        await self._invalidate_cache(flag.name)
        await self._set_cache(flag)
        logger.info(
            "feature_flag_toggled",
            name=flag.name,
            is_enabled=flag.is_enabled,
        )
        return flag

    # ── 評価ロジック ─────────────────────────────────────────────────────────

    def evaluate(
        self,
        flag_data: dict[str, Any] | FeatureFlag,
        *,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ) -> FeatureFlagEvaluation:
        """Feature Flag を評価する（有効/無効を判定する）。

        評価順序:
        1. is_enabled=False → 無効
        2. tenant_id 不一致 → 無効
        3. rollout_percentage < 100 → ユーザーIDハッシュで判定
        4. それ以外 → 有効

        Args:
            flag_data: FeatureFlag インスタンスまたはキャッシュデータ dict
            user_id: ユーザーID（カナリア割合判定に使用）
            tenant_id: 現在のテナントID

        Returns:
            FeatureFlagEvaluation
        """
        if isinstance(flag_data, FeatureFlag):
            name = flag_data.name
            is_enabled = flag_data.is_enabled
            rollout = flag_data.rollout_percentage
            flag_tenant = str(flag_data.tenant_id) if flag_data.tenant_id else None
        else:
            name = flag_data.get("name", "unknown")
            is_enabled = flag_data.get("is_enabled", False)
            rollout = flag_data.get("rollout_percentage", 100.0)
            flag_tenant = flag_data.get("tenant_id")

        if not is_enabled:
            return FeatureFlagEvaluation(
                flag_name=name,
                is_active=False,
                reason="disabled",
            )

        # テナント限定チェック
        if flag_tenant is not None and tenant_id != flag_tenant:
            return FeatureFlagEvaluation(
                flag_name=name,
                is_active=False,
                reason="tenant_mismatch",
            )

        # カナリアロールアウト: ユーザーIDのハッシュで一貫した割り当て
        if rollout < 100.0:
            if user_id is None:
                return FeatureFlagEvaluation(
                    flag_name=name,
                    is_active=False,
                    reason="rollout_no_user_id",
                )
            # SHA-256 の上位32ビットを 0〜100 にマップ
            hash_val = int(hashlib.sha256(user_id.encode()).hexdigest()[:8], 16)
            bucket = (hash_val % 10000) / 100.0  # 0.00〜99.99
            if bucket >= rollout:
                return FeatureFlagEvaluation(
                    flag_name=name,
                    is_active=False,
                    reason=f"rollout_excluded (bucket={bucket:.2f}% >= {rollout}%)",
                )

        return FeatureFlagEvaluation(
            flag_name=name,
            is_active=True,
            reason="enabled",
        )

    async def is_active(
        self,
        flag_name: str,
        *,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        """フラグが有効かどうかをシンプルに返す（キャッシュ優先）。"""
        # キャッシュ確認
        cached = await self._get_from_cache(flag_name)
        if cached is not None:
            cached["name"] = flag_name
            evaluation = self.evaluate(cached, user_id=user_id, tenant_id=tenant_id)
            return evaluation.is_active

        # DB から取得
        flag = await self.get_by_name(flag_name)
        if flag is None:
            logger.debug("feature_flag_not_found", name=flag_name)
            return False

        await self._set_cache(flag)
        evaluation = self.evaluate(flag, user_id=user_id, tenant_id=tenant_id)
        return evaluation.is_active
