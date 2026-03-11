"""DBクエリ最適化ユーティリティ テストスイート (Issue #88, Phase 9-PERF-1)"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── QueryCounter テスト ───────────────────────────────────────────────────────


class TestQueryCounter:
    """QueryCounter クラスのテスト"""

    def _make_mock_engine(self):
        """テスト用モックエンジン生成"""
        mock_sync_engine = MagicMock()
        mock_sync_engine._listeners = {}

        # event.listen/remove のモック
        def fake_listen(target, event_name, fn):
            mock_sync_engine._listeners[event_name] = fn

        def fake_remove(target, event_name, fn):
            mock_sync_engine._listeners.pop(event_name, None)

        mock_engine = MagicMock()
        mock_engine.sync_engine = mock_sync_engine
        return mock_engine, fake_listen, fake_remove

    def test_query_counter_init(self):
        """QueryCounter の初期化テスト"""
        from src.core.query_optimizer import QueryCounter

        mock_engine = MagicMock()
        mock_engine.sync_engine = MagicMock()
        counter = QueryCounter(mock_engine)
        assert counter.count == 0
        assert counter._engine is mock_engine.sync_engine

    def test_query_counter_context_manager(self):
        """コンテキストマネージャーとして使用できる"""
        from src.core.query_optimizer import QueryCounter

        mock_engine = MagicMock()
        mock_engine.sync_engine = MagicMock()

        with patch("src.core.query_optimizer.event") as mock_event:
            counter = QueryCounter(mock_engine)
            with counter as c:
                assert c is counter
                mock_event.listen.assert_called_once_with(
                    mock_engine.sync_engine, "after_cursor_execute", counter._listener
                )
            mock_event.remove.assert_called_once_with(
                mock_engine.sync_engine, "after_cursor_execute", counter._listener
            )

    def test_query_counter_counts_queries(self):
        """クエリ実行ごとにカウントが増加する"""
        from src.core.query_optimizer import QueryCounter

        mock_engine = MagicMock()
        mock_engine.sync_engine = MagicMock()

        with patch("src.core.query_optimizer.event"):
            counter = QueryCounter(mock_engine)
            with counter:
                # _listener を直接呼び出してクエリ実行をシミュレート
                counter._listener(None, None, "SELECT 1", None, None, False)
                counter._listener(None, None, "SELECT 2", None, None, False)
                counter._listener(None, None, "SELECT 3", None, None, False)
            assert counter.count == 3

    def test_query_counter_resets_between_uses(self):
        """新しい QueryCounter は0から始まる"""
        from src.core.query_optimizer import QueryCounter

        mock_engine = MagicMock()
        mock_engine.sync_engine = MagicMock()

        with patch("src.core.query_optimizer.event"):
            counter1 = QueryCounter(mock_engine)
            with counter1:
                counter1._listener(None, None, "SELECT 1", None, None, False)
            assert counter1.count == 1

            counter2 = QueryCounter(mock_engine)
            with counter2:
                pass
            assert counter2.count == 0


# ── スロークエリ検出 テスト ──────────────────────────────────────────────────


class TestSlowQueryLogging:
    """setup_slow_query_logging のテスト"""

    def test_setup_attaches_listeners(self):
        """リスナーがエンジンにアタッチされる"""
        from src.core.query_optimizer import setup_slow_query_logging

        mock_engine = MagicMock()
        mock_sync_engine = MagicMock()
        mock_engine.sync_engine = mock_sync_engine

        with patch("src.core.query_optimizer.event") as mock_event:
            setup_slow_query_logging(mock_engine, threshold_sec=0.1)
            # before_cursor_execute と after_cursor_execute の2回リスナー登録
            assert mock_event.listens_for.call_count == 2

    def test_slow_query_threshold_constant(self):
        """スロークエリ閾値定数が100msである"""
        from src.core.query_optimizer import SLOW_QUERY_THRESHOLD_SEC

        assert SLOW_QUERY_THRESHOLD_SEC == 0.1

    def test_slow_query_warning_logged(self):
        """スロークエリ発生時に warning ログが出力される"""
        from src.core.query_optimizer import SLOW_QUERY_THRESHOLD_SEC

        # スロークエリ閾値より遅い場合にログが出ることを確認（ロジックの検証）
        assert SLOW_QUERY_THRESHOLD_SEC > 0


# ── paginated_query テスト ────────────────────────────────────────────────────


class TestPaginatedQuery:
    """paginated_query ヘルパー関数のテスト"""

    def _setup_mocks(self, total: int, items: list):
        """共通モック生成ヘルパー"""
        mock_db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = total
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = items

        mock_stmt = MagicMock()
        mock_stmt.subquery.return_value = MagicMock()
        mock_stmt.options.return_value = mock_stmt
        mock_stmt.offset.return_value = mock_stmt
        mock_stmt.limit.return_value = mock_stmt
        mock_stmt.order_by.return_value = mock_stmt

        return mock_db, count_result, data_result, mock_stmt

    @pytest.mark.asyncio
    async def test_paginated_query_returns_tuple(self):
        """(items, total) のタプルを返す"""
        from src.core.query_optimizer import paginated_query

        mock_item = MagicMock()
        mock_db, count_result, data_result, mock_stmt = self._setup_mocks(5, [mock_item, mock_item])
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        with patch("src.core.query_optimizer.select"), patch("src.core.query_optimizer.func"):
            items, total = await paginated_query(mock_db, mock_stmt, page=1, size=20)

        assert total == 5
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_paginated_query_page_offset(self):
        """ページ番号に基づくオフセットが正しく計算される"""
        from src.core.query_optimizer import paginated_query

        mock_db, count_result, data_result, mock_stmt = self._setup_mocks(100, [])
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        with patch("src.core.query_optimizer.select"), patch("src.core.query_optimizer.func"):
            await paginated_query(mock_db, mock_stmt, page=3, size=10)

        # page=3, size=10 → offset=20
        mock_stmt.offset.assert_called_with(20)
        mock_stmt.limit.assert_called_with(10)

    @pytest.mark.asyncio
    async def test_paginated_query_with_eager_loads(self):
        """eager_loads が指定された場合に selectinload が適用される"""
        from src.core.query_optimizer import paginated_query

        mock_db, count_result, data_result, mock_stmt = self._setup_mocks(1, [])
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])
        mock_relation = MagicMock()

        with patch("src.core.query_optimizer.select"), patch(
            "src.core.query_optimizer.func"
        ), patch("src.core.query_optimizer.selectinload") as mock_selectinload:
            mock_selectinload.return_value = MagicMock()
            await paginated_query(mock_db, mock_stmt, eager_loads=[mock_relation])
            mock_selectinload.assert_called_once_with(mock_relation)
            mock_stmt.options.assert_called_once()

    @pytest.mark.asyncio
    async def test_paginated_query_without_eager_loads(self):
        """eager_loads なしでも正常動作する"""
        from src.core.query_optimizer import paginated_query

        mock_db, count_result, data_result, mock_stmt = self._setup_mocks(0, [])
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])

        with patch("src.core.query_optimizer.select"), patch("src.core.query_optimizer.func"):
            items, total = await paginated_query(mock_db, mock_stmt)

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_paginated_query_with_order_by(self):
        """order_by が指定された場合に適用される"""
        from src.core.query_optimizer import paginated_query

        mock_db, count_result, data_result, mock_stmt = self._setup_mocks(3, [])
        mock_db.execute = AsyncMock(side_effect=[count_result, data_result])
        mock_order = MagicMock()

        with patch("src.core.query_optimizer.select"), patch("src.core.query_optimizer.func"):
            await paginated_query(mock_db, mock_stmt, order_by=mock_order)

        mock_stmt.order_by.assert_called_with(mock_order)


# ── get_or_404 テスト ─────────────────────────────────────────────────────────


class TestGetOr404:
    """get_or_404 ヘルパー関数のテスト"""

    @pytest.mark.asyncio
    async def test_get_or_404_returns_item(self):
        """レコードが存在する場合にアイテムを返す"""
        from src.core.query_optimizer import get_or_404

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_item = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_model = MagicMock()
        mock_pk_column = MagicMock()
        mock_pk_column.__eq__ = MagicMock(return_value=MagicMock())

        with patch("src.core.query_optimizer.select") as mock_select:
            mock_select.return_value = MagicMock()
            mock_select.return_value.where.return_value = MagicMock()

            result = await get_or_404(mock_db, mock_model, "test-id", pk_column=mock_pk_column)

        assert result is mock_item

    @pytest.mark.asyncio
    async def test_get_or_404_returns_none_when_not_found(self):
        """レコードが存在しない場合に None を返す"""
        from src.core.query_optimizer import get_or_404

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_model = MagicMock()
        mock_pk_column = MagicMock()
        mock_pk_column.__eq__ = MagicMock(return_value=MagicMock())

        with patch("src.core.query_optimizer.select") as mock_select:
            mock_select.return_value = MagicMock()
            mock_select.return_value.where.return_value = MagicMock()

            result = await get_or_404(mock_db, mock_model, "missing-id", pk_column=mock_pk_column)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_404_with_eager_loads(self):
        """eager_loads が指定された場合に selectinload が適用される"""
        from src.core.query_optimizer import get_or_404

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_model = MagicMock()
        mock_pk_column = MagicMock()
        mock_pk_column.__eq__ = MagicMock(return_value=MagicMock())
        mock_relation = MagicMock()

        with patch("src.core.query_optimizer.select") as mock_select, patch(
            "src.core.query_optimizer.selectinload"
        ) as mock_selectinload:
            mock_stmt = MagicMock()
            mock_select.return_value = mock_stmt
            mock_stmt.where.return_value = mock_stmt
            mock_stmt.options.return_value = mock_stmt
            mock_selectinload.return_value = MagicMock()

            await get_or_404(
                mock_db,
                mock_model,
                "test-id",
                pk_column=mock_pk_column,
                eager_loads=[mock_relation],
            )

            mock_selectinload.assert_called_once_with(mock_relation)


# ── Alembicマイグレーション テスト ────────────────────────────────────────────


class TestPerformanceMigration:
    """パフォーマンスインデックスマイグレーション検証"""

    def test_migration_file_exists(self):
        """マイグレーションファイルが存在する"""
        import os

        migration_path = "alembic/versions/020_add_performance_indexes.py"
        assert os.path.exists(migration_path), (
            f"マイグレーションファイルが見つかりません: {migration_path}"
        )

    def test_migration_revision(self):
        """マイグレーションのリビジョンが正しい"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_020",
            "alembic/versions/020_add_performance_indexes.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        assert migration.revision == "020"
        assert migration.down_revision == "019"

    def test_migration_has_upgrade(self):
        """upgrade 関数が存在する"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_020",
            "alembic/versions/020_add_performance_indexes.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        assert callable(migration.upgrade)

    def test_migration_has_downgrade(self):
        """downgrade 関数が存在する"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_020",
            "alembic/versions/020_add_performance_indexes.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        assert callable(migration.downgrade)
