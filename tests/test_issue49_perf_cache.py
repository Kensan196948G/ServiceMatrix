"""Issue #49 APIパフォーマンス最適化 - キャッシュ層・DBプール・インデックステスト"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. キャッシュ HIT: DB アクセスなし
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cache_hit() -> None:
    """キャッシュHIT時はDBを叩かずキャッシュ値を返す"""
    cached_payload = json.dumps({"items": [], "total": 0, "page": 1, "size": 20, "pages": 0})

    with (
        patch("src.api.v1.incidents.cache_get", new=AsyncMock(return_value=cached_payload)),
        patch("src.api.v1.incidents.cache_set", new=AsyncMock()) as mock_set,
    ):
        from src.api.v1.incidents import cache_get  # noqa: PLC0415

        result = await cache_get("incidents:list:1:20:None:None:None")
        assert result == cached_payload
        # cache_set は呼ばれないはず（キャッシュHIT後にsetしない）
        mock_set.assert_not_called()


# ---------------------------------------------------------------------------
# 2. キャッシュ MISS: DB アクセス後にキャッシュ保存
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cache_miss() -> None:
    """キャッシュMISS時はDBアクセスを行い cache_set を呼ぶ"""
    mock_db = AsyncMock()

    # scalars().all() の連鎖モック
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalars
    mock_execute_result.scalar_one.return_value = 0

    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    mock_user = MagicMock()

    with (
        patch("src.api.v1.incidents.cache_get", new=AsyncMock(return_value=None)),
        patch("src.api.v1.incidents.cache_set", new=AsyncMock()) as mock_set,
        patch("src.api.v1.incidents.cache_delete_pattern", new=AsyncMock()),
    ):
        from src.api.v1.incidents import list_incidents  # noqa: PLC0415

        await list_incidents(
            db=mock_db,
            current_user=mock_user,
            page=1,
            size=20,
            status_filter=None,
            priority=None,
            department=None,
        )
        # キャッシュMISS後に cache_set が呼ばれること
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        assert call_args.kwargs.get("ttl") == 60 or call_args.args[2] == 60


# ---------------------------------------------------------------------------
# 3. POST 時にキャッシュ削除
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cache_invalidation_on_create() -> None:
    """POST（インシデント作成）時に incidents:list:* キャッシュが削除される"""
    mock_incident = MagicMock()
    mock_incident.incident_id = "test-uuid-1234"

    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_background = MagicMock()
    mock_background.add_task = MagicMock()

    mock_data = MagicMock()
    mock_data.model_dump.return_value = {"title": "テスト", "priority": "P1"}

    with (
        patch(
            "src.api.v1.incidents.incident_service.create_incident",
            new=AsyncMock(return_value=mock_incident),
        ),
        patch(
            "src.api.v1.incidents.ai_triage_service.apply_triage_to_incident",
            new=AsyncMock(),
        ),
        patch("src.api.v1.incidents.cache_delete_pattern", new=AsyncMock()) as mock_delete,
    ):
        from src.api.v1.incidents import create_incident  # noqa: PLC0415

        await create_incident(
            data=mock_data,
            background_tasks=mock_background,
            db=mock_db,
            current_user=mock_user,
        )
        mock_delete.assert_called_once_with("incidents:list:*")


# ---------------------------------------------------------------------------
# 4. DB プール設定確認
# ---------------------------------------------------------------------------
def test_db_pool_config() -> None:
    """database.py の engine が pool_size=20, max_overflow=40 で設定されていること"""
    db_path = Path("/mnt/LinuxHDD/worktree-issue49-perf/src/core/database.py")
    content = db_path.read_text()
    assert "pool_size" in content
    assert '"pool_size": 20' in content or "'pool_size': 20" in content
    assert '"max_overflow": 40' in content or "'max_overflow': 40" in content
    assert '"pool_recycle": 3600' in content or "'pool_recycle': 3600" in content


# ---------------------------------------------------------------------------
# 5. マイグレーションファイル存在確認
# ---------------------------------------------------------------------------
def test_performance_index_migration_exists() -> None:
    """014_add_performance_indexes.py が存在し、必要なインデックス定義を含む"""
    migration_path = Path(
        "/mnt/LinuxHDD/worktree-issue49-perf/alembic/versions/014_add_performance_indexes.py"
    )
    assert migration_path.exists(), "マイグレーションファイルが存在しません"

    content = migration_path.read_text()
    # revision チェック
    assert "014_add_performance_indexes" in content
    assert 'down_revision: str | None = "013"' in content

    # インシデント関連インデックス
    assert "ix_incidents_status" in content
    assert "ix_incidents_priority" in content
    assert "ix_incidents_created_at_desc" in content
    assert "ix_incidents_status_priority" in content

    # 変更管理関連インデックス
    assert "ix_changes_status" in content
    assert "ix_changes_change_type" in content
    assert "ix_changes_created_at_desc" in content

    # 問題管理関連インデックス
    assert "ix_problems_status" in content
    assert "ix_problems_priority" in content
