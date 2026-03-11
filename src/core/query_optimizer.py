"""クエリ最適化ユーティリティ - N+1問題解消・スロークエリ検出

実装方針:
- SQLAlchemy event listener でクエリ実行時間を計測
- スロークエリ（デフォルト100ms以上）をwarningログ出力
- よく使うクエリパターンのヘルパー関数を提供
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import event, func, select
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = structlog.get_logger(__name__)

# スロークエリ閾値（秒）
SLOW_QUERY_THRESHOLD_SEC = 0.1


# ── スロークエリ検出 ─────────────────────────────────────────────────────────


def setup_slow_query_logging(
    engine: AsyncEngine,
    threshold_sec: float = SLOW_QUERY_THRESHOLD_SEC,
) -> None:
    """SQLAlchemy エンジンにスロークエリ検出リスナーを設定する。

    Args:
        engine: 対象の AsyncEngine
        threshold_sec: スロークエリとみなす秒数（デフォルト0.1秒）
    """
    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.monotonic())

    @event.listens_for(sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_sec = time.monotonic() - conn.info["query_start_time"].pop(-1)
        if total_sec >= threshold_sec:
            logger.warning(
                "slow_query_detected",
                duration_ms=round(total_sec * 1000, 2),
                threshold_ms=round(threshold_sec * 1000),
                statement=statement[:200],
            )


# ── 最適化クエリヘルパー ─────────────────────────────────────────────────────


async def paginated_query(
    db: AsyncSession,
    base_stmt,
    page: int = 1,
    size: int = 20,
    *,
    order_by=None,
    eager_loads: list | None = None,
) -> tuple[list[Any], int]:
    """ページネーション付きクエリを実行する。

    N+1問題を避けるため、eager_loads で selectinload を指定できる。

    Args:
        db: 非同期セッション
        base_stmt: フィルタ済みの select 文
        page: ページ番号（1始まり）
        size: 1ページあたりの件数
        order_by: ソート列（省略時は None）
        eager_loads: selectinload するリレーション属性のリスト

    Returns:
        (items, total) のタプル

    Example:
        items, total = await paginated_query(
            db,
            select(Incident).where(Incident.status == "New"),
            page=1,
            size=20,
            order_by=Incident.created_at.desc(),
            eager_loads=[Incident.assignee, Incident.assigned_team],
        )
    """
    # 総件数: サブクエリでカウント
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # データ取得: eager loading + ページネーション
    data_stmt = base_stmt
    if eager_loads:
        for relation in eager_loads:
            data_stmt = data_stmt.options(selectinload(relation))
    if order_by is not None:
        data_stmt = data_stmt.order_by(order_by)
    data_stmt = data_stmt.offset((page - 1) * size).limit(size)

    result = await db.execute(data_stmt)
    items = result.scalars().all()

    return list(items), total


async def get_or_404(
    db: AsyncSession,
    model_class,
    pk_value: Any,
    pk_column=None,
    *,
    eager_loads: list | None = None,
) -> Any:
    """主キーでレコードを取得し、存在しない場合は None を返す。

    Args:
        db: 非同期セッション
        model_class: SQLAlchemy モデルクラス
        pk_value: 主キー値
        pk_column: 主キーカラム（省略時はモデルの最初の主キー）
        eager_loads: selectinload するリレーション

    Returns:
        モデルインスタンス（存在しない場合は None）
    """
    if pk_column is None:
        # モデルの主キーカラムを自動解決
        from sqlalchemy import inspect as sa_inspect

        mapper = sa_inspect(model_class)
        pk_cols = mapper.primary_key
        if not pk_cols:
            raise ValueError(f"{model_class.__name__} に主キーが見つかりません")
        pk_column = getattr(model_class, pk_cols[0].name)

    stmt = select(model_class).where(pk_column == pk_value)
    if eager_loads:
        for relation in eager_loads:
            stmt = stmt.options(selectinload(relation))

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── クエリカウンタ（テスト用） ────────────────────────────────────────────────


class QueryCounter:
    """テスト用クエリカウンタ。

    SQLAlchemy エンジンに一時的にリスナーを付けてクエリ数を計測する。

    Usage:
        counter = QueryCounter(engine)
        async with counter:
            # クエリ実行
            ...
        assert counter.count <= 3  # N+1が解消されていることを確認
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine.sync_engine
        self.count = 0

    def _listener(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1

    def __enter__(self) -> QueryCounter:
        event.listen(self._engine, "after_cursor_execute", self._listener)
        return self

    def __exit__(self, *args) -> None:
        event.remove(self._engine, "after_cursor_execute", self._listener)
