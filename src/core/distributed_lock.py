"""分散ロック実装 - Redis SET NX EX パターン (Issue #89, Phase 9-DIST-1)

実装方針:
- Redis SET key value NX EX ttl でアトミックなロック取得
- Luaスクリプトで所有者確認付きリリース（解放競合防止）
- コンテキストマネージャで安全な acquire/release
- Redis未接続時は LockUnavailableError を発生させる（サイレント失敗防止）
"""

from __future__ import annotations

import secrets
import time
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)

# Lua スクリプト: 所有者一致時のみ削除
_RELEASE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class LockAcquireError(RuntimeError):
    """ロック取得失敗"""


class LockUnavailableError(RuntimeError):
    """Redis 未接続などでロック機能が利用不可"""


class DistributedLock:
    """Redis を使用した分散ロック。

    Usage:
        lock = DistributedLock(redis_client, "sla:monitor:lock", ttl=30)
        async with lock:
            # クリティカルセクション
            ...

        # または明示的 acquire/release
        acquired = await lock.acquire()
        if acquired:
            try:
                ...
            finally:
                await lock.release()
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        name: str,
        ttl: int = 30,
        retry_count: int = 3,
        retry_delay: float = 0.1,
    ) -> None:
        """
        Args:
            redis_client: Redis 非同期クライアント
            name: ロックキー名（一意な識別子）
            ttl: ロック有効期間（秒）。TTL を超えると自動解放される
            retry_count: acquire 失敗時の再試行回数
            retry_delay: 再試行間隔（秒）
        """
        self._redis = redis_client
        self._name = f"lock:{name}"
        self._ttl = ttl
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        # ランダムな所有者識別子（UUID-like）でリリース時の不正解放を防ぐ
        self._owner_id = secrets.token_hex(16)
        self._acquired = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_acquired(self) -> bool:
        return self._acquired

    async def acquire(self) -> bool:
        """ロック取得を試みる。

        Returns:
            True: ロック取得成功
            False: タイムアウト（retry_count 回試行後）

        Raises:
            LockUnavailableError: Redis 接続エラー
        """
        for attempt in range(self._retry_count):
            try:
                result = await self._redis.set(
                    self._name,
                    self._owner_id,
                    nx=True,  # Not eXists: キーが存在しない場合のみ SET
                    ex=self._ttl,  # Expire: TTL 後に自動削除
                )
                if result:
                    self._acquired = True
                    logger.debug(
                        "distributed_lock_acquired",
                        lock=self._name,
                        ttl=self._ttl,
                        attempt=attempt + 1,
                    )
                    return True
            except Exception as exc:
                raise LockUnavailableError(f"Redis 接続エラー: {exc}") from exc

            if attempt < self._retry_count - 1:
                await _async_sleep(self._retry_delay)

        logger.warning(
            "distributed_lock_acquire_failed",
            lock=self._name,
            retry_count=self._retry_count,
        )
        return False

    async def release(self) -> None:
        """ロックを解放する。所有者確認（Lua スクリプト）により
        他インスタンスのロックを誤解放しない。

        Raises:
            LockUnavailableError: Redis 接続エラー
        """
        if not self._acquired:
            return
        try:
            deleted = await self._redis.eval(_RELEASE_SCRIPT, 1, self._name, self._owner_id)
            if deleted:
                logger.debug("distributed_lock_released", lock=self._name)
            else:
                logger.warning(
                    "distributed_lock_release_skipped",
                    lock=self._name,
                    reason="TTL expired or owned by another instance",
                )
        except Exception as exc:
            raise LockUnavailableError(f"Redis 接続エラー (release): {exc}") from exc
        finally:
            self._acquired = False

    async def __aenter__(self) -> DistributedLock:
        acquired = await self.acquire()
        if not acquired:
            raise LockAcquireError(f"ロック取得失敗: {self._name} ({self._retry_count} 回試行)")
        return self

    async def __aexit__(self, *args) -> None:
        await self.release()


# ── インメモリフォールバック（開発・テスト用）──────────────────────────────


class InMemoryLock:
    """Redis 未使用環境向けインメモリ分散ロック（シングルプロセス用）。

    本番環境では DistributedLock を使用すること。
    """

    _locks: dict[str, tuple[str, float]] = {}

    def __init__(
        self,
        name: str,
        ttl: int = 30,
        retry_count: int = 3,
        retry_delay: float = 0.1,
    ) -> None:
        self._name = f"lock:{name}"
        self._ttl = ttl
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._owner_id = secrets.token_hex(16)
        self._acquired = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_acquired(self) -> bool:
        return self._acquired

    async def acquire(self) -> bool:
        for attempt in range(self._retry_count):
            now = time.monotonic()
            # 期限切れロックを削除
            if self._name in InMemoryLock._locks:
                _, expires_at = InMemoryLock._locks[self._name]
                if now >= expires_at:
                    del InMemoryLock._locks[self._name]

            if self._name not in InMemoryLock._locks:
                InMemoryLock._locks[self._name] = (
                    self._owner_id,
                    now + self._ttl,
                )
                self._acquired = True
                return True

            if attempt < self._retry_count - 1:
                await _async_sleep(self._retry_delay)

        return False

    async def release(self) -> None:
        if not self._acquired:
            return
        entry = InMemoryLock._locks.get(self._name)
        if entry and entry[0] == self._owner_id:
            del InMemoryLock._locks[self._name]
        self._acquired = False

    async def __aenter__(self) -> InMemoryLock:
        acquired = await self.acquire()
        if not acquired:
            raise LockAcquireError(f"ロック取得失敗: {self._name}")
        return self

    async def __aexit__(self, *args) -> None:
        await self.release()


# ── ユーティリティ ────────────────────────────────────────────────────────


async def _async_sleep(delay: float) -> None:
    """asyncio.sleep のラッパー（テスト時のモック対象）"""
    import asyncio

    await asyncio.sleep(delay)
