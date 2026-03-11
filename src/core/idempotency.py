"""冪等性キー検証 - 重複リクエスト防止 (Issue #89, Phase 9-DIST-1)

実装方針:
- Idempotency-Key ヘッダーでリクエストを識別
- Redis に処理結果をキャッシュ（TTL: 24時間）
- 重複リクエストにはキャッシュ済み結果を返す
- キーフォーマット: "idempotency:{client_id}:{key}"
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)

# 冪等性キーの有効期間（24時間）
IDEMPOTENCY_TTL_SEC = 86400

# キーの最大長（セキュリティ上限）
MAX_KEY_LENGTH = 255


class IdempotencyError(ValueError):
    """冪等性キー検証エラー"""


class IdempotencyStore:
    """Redis を使用した冪等性キー管理。

    Usage:
        store = IdempotencyStore(redis_client)

        # リクエスト処理前
        cached = await store.get("user-123", "req-abc-456")
        if cached is not None:
            return cached  # 重複リクエスト: キャッシュ済み結果を返す

        # 処理実行
        result = await do_something()

        # 結果を保存
        await store.save("user-123", "req-abc-456", result)
        return result
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        ttl: int = IDEMPOTENCY_TTL_SEC,
        key_prefix: str = "idempotency",
    ) -> None:
        """
        Args:
            redis_client: Redis 非同期クライアント
            ttl: キャッシュ有効期間（秒）
            key_prefix: Redis キー プレフィックス
        """
        self._redis = redis_client
        self._ttl = ttl
        self._key_prefix = key_prefix

    def _build_key(self, client_id: str, idempotency_key: str) -> str:
        """Redis キーを構築する。"""
        return f"{self._key_prefix}:{client_id}:{idempotency_key}"

    @staticmethod
    def validate_key(key: str) -> str:
        """冪等性キーのバリデーション。

        Args:
            key: 検証するキー文字列

        Returns:
            検証済みキー

        Raises:
            IdempotencyError: キーが不正な場合
        """
        if not key:
            raise IdempotencyError("冪等性キーが空です")
        if len(key) > MAX_KEY_LENGTH:
            raise IdempotencyError(
                f"冪等性キーが最大長 {MAX_KEY_LENGTH} を超えています: {len(key)}"
            )
        # 基本的なサニタイズ（Redis キーに使用できない文字を排除）
        stripped = key.strip()
        if not stripped:
            raise IdempotencyError("冪等性キーが空白のみです")
        return stripped

    async def get(self, client_id: str, idempotency_key: str) -> Any | None:
        """保存済み処理結果を取得する。

        Args:
            client_id: クライアント識別子（ユーザーIDなど）
            idempotency_key: 冪等性キー（リクエスト固有ID）

        Returns:
            保存済み結果（なければ None）

        Raises:
            IdempotencyError: キーが不正
        """
        validated_key = self.validate_key(idempotency_key)
        redis_key = self._build_key(client_id, validated_key)
        try:
            raw = await self._redis.get(redis_key)
            if raw is None:
                return None
            result = json.loads(raw)
            logger.info(
                "idempotency_cache_hit",
                client_id=client_id,
                key=validated_key,
            )
            return result
        except json.JSONDecodeError as exc:
            logger.error(
                "idempotency_cache_corrupt",
                client_id=client_id,
                key=validated_key,
                error=str(exc),
            )
            return None

    async def save(
        self,
        client_id: str,
        idempotency_key: str,
        result: Any,
    ) -> None:
        """処理結果を保存する。

        Args:
            client_id: クライアント識別子
            idempotency_key: 冪等性キー
            result: 保存する処理結果（JSON シリアライズ可能である必要がある）

        Raises:
            IdempotencyError: キーが不正または結果がシリアライズ不可
        """
        validated_key = self.validate_key(idempotency_key)
        redis_key = self._build_key(client_id, validated_key)
        try:
            serialized = json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise IdempotencyError(f"処理結果のシリアライズ失敗: {exc}") from exc

        await self._redis.setex(redis_key, self._ttl, serialized)
        logger.debug(
            "idempotency_result_saved",
            client_id=client_id,
            key=validated_key,
            ttl=self._ttl,
        )

    async def delete(self, client_id: str, idempotency_key: str) -> bool:
        """保存済み結果を削除する（テスト・管理用）。

        Returns:
            True: 削除成功、False: キーが存在しなかった
        """
        validated_key = self.validate_key(idempotency_key)
        redis_key = self._build_key(client_id, validated_key)
        deleted = await self._redis.delete(redis_key)
        return bool(deleted)

    async def exists(self, client_id: str, idempotency_key: str) -> bool:
        """冪等性キーが存在するか確認する。"""
        validated_key = self.validate_key(idempotency_key)
        redis_key = self._build_key(client_id, validated_key)
        count = await self._redis.exists(redis_key)
        return bool(count)


# ── インメモリフォールバック（開発・テスト用）──────────────────────────────


class InMemoryIdempotencyStore:
    """Redis 未使用環境向けインメモリ冪等性ストア（シングルプロセス用）。"""

    import time as _time

    def __init__(self, ttl: int = IDEMPOTENCY_TTL_SEC) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[Any, float]] = {}

    def _build_key(self, client_id: str, idempotency_key: str) -> str:
        return f"{client_id}:{idempotency_key}"

    def _evict_expired(self) -> None:
        import time

        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now >= exp]
        for k in expired:
            del self._store[k]

    async def get(self, client_id: str, idempotency_key: str) -> Any | None:
        import time

        IdempotencyStore.validate_key(idempotency_key)
        self._evict_expired()
        key = self._build_key(client_id, idempotency_key)
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return None
        return value

    async def save(
        self,
        client_id: str,
        idempotency_key: str,
        result: Any,
    ) -> None:
        import time

        IdempotencyStore.validate_key(idempotency_key)
        key = self._build_key(client_id, idempotency_key)
        self._store[key] = (result, time.monotonic() + self._ttl)

    async def delete(self, client_id: str, idempotency_key: str) -> bool:
        IdempotencyStore.validate_key(idempotency_key)
        key = self._build_key(client_id, idempotency_key)
        return self._store.pop(key, None) is not None

    async def exists(self, client_id: str, idempotency_key: str) -> bool:
        IdempotencyStore.validate_key(idempotency_key)
        result = await self.get(client_id, idempotency_key)
        return result is not None
