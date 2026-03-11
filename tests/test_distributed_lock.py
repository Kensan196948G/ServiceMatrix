"""分散ロック・冪等性検証 テストスイート (Issue #89, Phase 9-DIST-1)"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ── DistributedLock テスト ─────────────────────────────────────────────────


class TestDistributedLockAcquire:
    """DistributedLock.acquire のテスト"""

    def _make_redis(self, set_return=True):
        """テスト用 Redis モック生成"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=set_return)
        mock_redis.eval = AsyncMock(return_value=1)
        return mock_redis

    @pytest.mark.asyncio
    async def test_acquire_success(self):
        """ロック取得成功: Redis SET NX が True を返す"""
        from src.core.distributed_lock import DistributedLock

        redis = self._make_redis(set_return=True)
        lock = DistributedLock(redis, "test-lock", ttl=30)
        result = await lock.acquire()

        assert result is True
        assert lock.is_acquired is True
        redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_failure_all_retries(self):
        """全リトライ失敗: False を返す"""
        from src.core.distributed_lock import DistributedLock

        redis = self._make_redis(set_return=False)
        with patch("src.core.distributed_lock._async_sleep", new=AsyncMock()):
            lock = DistributedLock(redis, "busy-lock", retry_count=3)
            result = await lock.acquire()

        assert result is False
        assert lock.is_acquired is False
        assert redis.set.call_count == 3

    @pytest.mark.asyncio
    async def test_acquire_second_attempt_succeeds(self):
        """2回目でロック取得成功"""
        from src.core.distributed_lock import DistributedLock

        redis = AsyncMock()
        redis.set = AsyncMock(side_effect=[False, True])
        with patch("src.core.distributed_lock._async_sleep", new=AsyncMock()):
            lock = DistributedLock(redis, "test-lock", retry_count=3)
            result = await lock.acquire()

        assert result is True
        assert lock.is_acquired is True
        assert redis.set.call_count == 2

    @pytest.mark.asyncio
    async def test_acquire_redis_error_raises(self):
        """Redis エラー時に LockUnavailableError を発生させる"""
        from src.core.distributed_lock import DistributedLock, LockUnavailableError

        redis = AsyncMock()
        redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))
        lock = DistributedLock(redis, "test-lock")

        with pytest.raises(LockUnavailableError):
            await lock.acquire()

    @pytest.mark.asyncio
    async def test_lock_key_prefix(self):
        """ロックキーに 'lock:' プレフィックスが付く"""
        from src.core.distributed_lock import DistributedLock

        redis = self._make_redis()
        lock = DistributedLock(redis, "my-resource")
        assert lock.name == "lock:my-resource"

    @pytest.mark.asyncio
    async def test_acquire_uses_nx_and_ex(self):
        """SET コマンドに NX=True, EX=ttl が設定される"""
        from src.core.distributed_lock import DistributedLock

        redis = self._make_redis()
        lock = DistributedLock(redis, "test-lock", ttl=60)
        await lock.acquire()

        call_kwargs = redis.set.call_args[1]
        assert call_kwargs["nx"] is True
        assert call_kwargs["ex"] == 60


class TestDistributedLockRelease:
    """DistributedLock.release のテスト"""

    def _make_acquired_lock(self, eval_return=1):
        """取得済みロックとモックRedisを返す"""
        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.eval = AsyncMock(return_value=eval_return)
        return redis

    @pytest.mark.asyncio
    async def test_release_success(self):
        """ロック解放成功"""
        from src.core.distributed_lock import DistributedLock

        redis = self._make_acquired_lock(eval_return=1)
        lock = DistributedLock(redis, "test-lock")
        await lock.acquire()
        await lock.release()

        assert lock.is_acquired is False
        redis.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_not_acquired_noop(self):
        """未取得状態でのリリースは何もしない"""
        from src.core.distributed_lock import DistributedLock

        redis = AsyncMock()
        lock = DistributedLock(redis, "test-lock")
        # acquire なしで release
        await lock.release()

        redis.eval.assert_not_called()

    @pytest.mark.asyncio
    async def test_release_redis_error_raises(self):
        """Redis エラー時に LockUnavailableError を発生させる"""
        from src.core.distributed_lock import DistributedLock, LockUnavailableError

        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.eval = AsyncMock(side_effect=ConnectionError("Redis down"))
        lock = DistributedLock(redis, "test-lock")
        await lock.acquire()

        with pytest.raises(LockUnavailableError):
            await lock.release()
        # acquired は False にリセットされる
        assert lock.is_acquired is False

    @pytest.mark.asyncio
    async def test_release_expired_lock_logs_warning(self):
        """TTL切れで他のインスタンスが保持中の場合（eval=0）は警告ログ"""
        from src.core.distributed_lock import DistributedLock

        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.eval = AsyncMock(return_value=0)  # 他インスタンスが所有
        lock = DistributedLock(redis, "test-lock")
        await lock.acquire()
        # 警告ログが出るが例外は発生しない
        await lock.release()
        assert lock.is_acquired is False


class TestDistributedLockContextManager:
    """DistributedLock コンテキストマネージャーのテスト"""

    @pytest.mark.asyncio
    async def test_context_manager_acquire_and_release(self):
        """コンテキストマネージャーで acquire/release が呼ばれる"""
        from src.core.distributed_lock import DistributedLock

        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.eval = AsyncMock(return_value=1)
        lock = DistributedLock(redis, "ctx-lock")

        async with lock as acquired_lock:
            assert acquired_lock is lock
            assert lock.is_acquired is True

        assert lock.is_acquired is False

    @pytest.mark.asyncio
    async def test_context_manager_raises_on_failure(self):
        """ロック取得失敗時に LockAcquireError を発生させる"""
        from src.core.distributed_lock import DistributedLock, LockAcquireError

        redis = AsyncMock()
        redis.set = AsyncMock(return_value=False)
        with patch("src.core.distributed_lock._async_sleep", new=AsyncMock()):
            lock = DistributedLock(redis, "busy-lock", retry_count=2)
            with pytest.raises(LockAcquireError):
                async with lock:
                    pass  # ここには到達しない

    @pytest.mark.asyncio
    async def test_context_manager_releases_on_exception(self):
        """例外発生時もロックが解放される"""
        from src.core.distributed_lock import DistributedLock

        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.eval = AsyncMock(return_value=1)
        lock = DistributedLock(redis, "test-lock")

        with pytest.raises(ValueError):
            async with lock:
                raise ValueError("処理エラー")

        assert lock.is_acquired is False
        redis.eval.assert_called_once()


# ── InMemoryLock テスト ────────────────────────────────────────────────────


class TestInMemoryLock:
    """InMemoryLock のテスト（Redis 不使用環境）"""

    def setup_method(self):
        """各テスト前にロックストアをクリア"""
        from src.core.distributed_lock import InMemoryLock

        InMemoryLock._locks.clear()

    @pytest.mark.asyncio
    async def test_acquire_success(self):
        """インメモリロック取得成功"""
        from src.core.distributed_lock import InMemoryLock

        lock = InMemoryLock("test-resource")
        result = await lock.acquire()
        assert result is True
        assert lock.is_acquired is True

    @pytest.mark.asyncio
    async def test_acquire_exclusive(self):
        """同じキーは排他制御される"""
        from src.core.distributed_lock import InMemoryLock

        with patch("src.core.distributed_lock._async_sleep", new=AsyncMock()):
            lock1 = InMemoryLock("shared", retry_count=1)
            lock2 = InMemoryLock("shared", retry_count=1)

            result1 = await lock1.acquire()
            result2 = await lock2.acquire()  # lock1 保持中

        assert result1 is True
        assert result2 is False

    @pytest.mark.asyncio
    async def test_release_allows_reacquire(self):
        """解放後に別インスタンスが取得できる"""
        from src.core.distributed_lock import InMemoryLock

        lock1 = InMemoryLock("resource")
        lock2 = InMemoryLock("resource")

        await lock1.acquire()
        await lock1.release()

        result = await lock2.acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_expired_lock_reacquirable(self):
        """TTL 切れロックは再取得可能"""
        from src.core.distributed_lock import InMemoryLock

        # TTL=0 で即時期限切れ
        lock1 = InMemoryLock("resource", ttl=0)
        lock2 = InMemoryLock("resource")

        await lock1.acquire()
        result = await lock2.acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """コンテキストマネージャーで動作"""
        from src.core.distributed_lock import InMemoryLock

        lock = InMemoryLock("ctx-resource")
        async with lock as acquired:
            assert acquired is lock
            assert lock.is_acquired is True

        assert lock.is_acquired is False


# ── IdempotencyStore テスト ────────────────────────────────────────────────


class TestIdempotencyStore:
    """IdempotencyStore のテスト"""

    def _make_redis(self):
        """テスト用 Redis モック"""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()
        redis.delete = AsyncMock(return_value=1)
        redis.exists = AsyncMock(return_value=0)
        return redis

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self):
        """キャッシュなし時に None を返す"""
        from src.core.idempotency import IdempotencyStore

        redis = self._make_redis()
        store = IdempotencyStore(redis)
        result = await store.get("user-1", "req-abc")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_cached_result(self):
        """キャッシュあり時に結果を返す"""
        from src.core.idempotency import IdempotencyStore

        redis = self._make_redis()
        import json

        redis.get = AsyncMock(return_value=json.dumps({"id": "INC-001", "status": "New"}).encode())
        store = IdempotencyStore(redis)
        result = await store.get("user-1", "req-abc")
        assert result == {"id": "INC-001", "status": "New"}

    @pytest.mark.asyncio
    async def test_save_stores_result(self):
        """処理結果を Redis に保存する"""
        from src.core.idempotency import IdempotencyStore

        redis = self._make_redis()
        store = IdempotencyStore(redis)
        await store.save("user-1", "req-abc", {"id": "INC-001"})
        redis.setex.assert_called_once()

        # キー形式の確認
        call_args = redis.setex.call_args[0]
        assert "idempotency:user-1:req-abc" == call_args[0]
        assert 86400 == call_args[1]  # デフォルトTTL

    @pytest.mark.asyncio
    async def test_save_unserializable_raises(self):
        """シリアライズ不可オブジェクトは IdempotencyError を発生させる"""
        from src.core.idempotency import IdempotencyError, IdempotencyStore

        redis = self._make_redis()
        store = IdempotencyStore(redis)

        class Unserializable:
            pass

        with pytest.raises(IdempotencyError):
            await store.save("user-1", "req-abc", Unserializable())

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        """存在するキーの削除"""
        from src.core.idempotency import IdempotencyStore

        redis = self._make_redis()
        redis.delete = AsyncMock(return_value=1)
        store = IdempotencyStore(redis)
        result = await store.delete("user-1", "req-abc")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_missing_key(self):
        """存在しないキーの削除は False を返す"""
        from src.core.idempotency import IdempotencyStore

        redis = self._make_redis()
        redis.delete = AsyncMock(return_value=0)
        store = IdempotencyStore(redis)
        result = await store.delete("user-1", "req-xyz")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true(self):
        """キーが存在する場合 True を返す"""
        from src.core.idempotency import IdempotencyStore

        redis = self._make_redis()
        redis.exists = AsyncMock(return_value=1)
        store = IdempotencyStore(redis)
        result = await store.exists("user-1", "req-abc")
        assert result is True

    @pytest.mark.asyncio
    async def test_corrupt_cache_returns_none(self):
        """破損キャッシュは None を返す（例外を発生させない）"""
        from src.core.idempotency import IdempotencyStore

        redis = self._make_redis()
        redis.get = AsyncMock(return_value=b"not-valid-json{{{")
        store = IdempotencyStore(redis)
        result = await store.get("user-1", "req-abc")
        assert result is None

    def test_validate_key_empty_raises(self):
        """空文字は IdempotencyError"""
        from src.core.idempotency import IdempotencyError, IdempotencyStore

        with pytest.raises(IdempotencyError):
            IdempotencyStore.validate_key("")

    def test_validate_key_too_long_raises(self):
        """最大長超過は IdempotencyError"""
        from src.core.idempotency import IdempotencyError, IdempotencyStore

        with pytest.raises(IdempotencyError):
            IdempotencyStore.validate_key("a" * 256)

    def test_validate_key_whitespace_raises(self):
        """空白のみは IdempotencyError"""
        from src.core.idempotency import IdempotencyError, IdempotencyStore

        with pytest.raises(IdempotencyError):
            IdempotencyStore.validate_key("   ")

    def test_validate_key_valid(self):
        """有効なキーはそのまま返す"""
        from src.core.idempotency import IdempotencyStore

        key = "req-abc-123"
        result = IdempotencyStore.validate_key(key)
        assert result == key


# ── InMemoryIdempotencyStore テスト ───────────────────────────────────────


class TestInMemoryIdempotencyStore:
    """InMemoryIdempotencyStore のテスト（Redis 不使用環境）"""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self):
        """キャッシュなし時に None を返す"""
        from src.core.idempotency import InMemoryIdempotencyStore

        store = InMemoryIdempotencyStore()
        result = await store.get("user-1", "req-abc")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_and_get(self):
        """保存した結果を取得できる"""
        from src.core.idempotency import InMemoryIdempotencyStore

        store = InMemoryIdempotencyStore()
        await store.save("user-1", "req-abc", {"status": "created"})
        result = await store.get("user-1", "req-abc")
        assert result == {"status": "created"}

    @pytest.mark.asyncio
    async def test_different_clients_isolated(self):
        """異なるクライアントのキャッシュは分離される"""
        from src.core.idempotency import InMemoryIdempotencyStore

        store = InMemoryIdempotencyStore()
        await store.save("user-1", "req-abc", "result-1")
        await store.save("user-2", "req-abc", "result-2")

        r1 = await store.get("user-1", "req-abc")
        r2 = await store.get("user-2", "req-abc")
        assert r1 == "result-1"
        assert r2 == "result-2"

    @pytest.mark.asyncio
    async def test_delete(self):
        """保存したキャッシュを削除できる"""
        from src.core.idempotency import InMemoryIdempotencyStore

        store = InMemoryIdempotencyStore()
        await store.save("user-1", "req-abc", "data")
        result = await store.delete("user-1", "req-abc")
        assert result is True
        assert await store.get("user-1", "req-abc") is None

    @pytest.mark.asyncio
    async def test_exists(self):
        """exists メソッドが正しく動作する"""
        from src.core.idempotency import InMemoryIdempotencyStore

        store = InMemoryIdempotencyStore()
        await store.save("user-1", "req-abc", "data")
        assert await store.exists("user-1", "req-abc") is True
        assert await store.exists("user-1", "req-xyz") is False
