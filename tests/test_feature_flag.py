"""Feature Flag システム テストスイート (Issue #90, Phase 9-DEPLOY-1)"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── FeatureFlagCreate スキーマテスト ──────────────────────────────────────


class TestFeatureFlagSchema:
    """スキーマバリデーションのテスト"""

    def test_create_valid(self):
        """有効なスキーマ作成"""
        from src.schemas.feature_flag import FeatureFlagCreate

        flag = FeatureFlagCreate(name="new_ui_v2", is_enabled=True, rollout_percentage=50.0)
        assert flag.name == "new_ui_v2"
        assert flag.is_enabled is True
        assert flag.rollout_percentage == 50.0

    def test_create_name_lowercased(self):
        """名前は小文字に変換される"""
        from src.schemas.feature_flag import FeatureFlagCreate

        flag = FeatureFlagCreate(name="new_ui_v2")
        assert flag.name == "new_ui_v2"

    def test_create_invalid_name_pattern(self):
        """無効な名前パターンはバリデーションエラー"""
        from pydantic import ValidationError

        from src.schemas.feature_flag import FeatureFlagCreate

        with pytest.raises(ValidationError):
            FeatureFlagCreate(name="Invalid Name!")  # スペース・感嘆符はNG

    def test_create_rollout_out_of_range(self):
        """ロールアウト割合が範囲外はバリデーションエラー"""
        from pydantic import ValidationError

        from src.schemas.feature_flag import FeatureFlagCreate

        with pytest.raises(ValidationError):
            FeatureFlagCreate(name="flag", rollout_percentage=101.0)

        with pytest.raises(ValidationError):
            FeatureFlagCreate(name="flag", rollout_percentage=-1.0)

    def test_create_with_tenant_id(self):
        """テナントID付きフラグ作成"""
        from src.schemas.feature_flag import FeatureFlagCreate

        tenant_id = uuid.uuid4()
        flag = FeatureFlagCreate(name="tenant_feature", tenant_id=tenant_id)
        assert flag.tenant_id == tenant_id

    def test_evaluation_response(self):
        """評価レスポンスのスキーマ"""
        from src.schemas.feature_flag import FeatureFlagEvaluation

        eval_result = FeatureFlagEvaluation(
            flag_name="my_flag",
            is_active=True,
            reason="enabled",
        )
        assert eval_result.is_active is True
        assert eval_result.flag_name == "my_flag"


# ── FeatureFlagModel テスト ────────────────────────────────────────────────


class TestFeatureFlagModel:
    """FeatureFlag モデルのテスト"""

    def test_model_repr(self):
        """__repr__ が正しく動作する"""
        from src.models.feature_flag import FeatureFlag

        flag = FeatureFlag()
        flag.name = "test_flag"
        flag.is_enabled = True
        flag.rollout_percentage = 75.0
        repr_str = repr(flag)
        assert "test_flag" in repr_str
        assert "True" in repr_str
        assert "75.0" in repr_str

    def test_model_default_values(self):
        """カラム定義にデフォルト値が設定されている"""
        from sqlalchemy import inspect as sa_inspect

        from src.models.feature_flag import FeatureFlag

        mapper = sa_inspect(FeatureFlag)
        columns = {col.name: col for col in mapper.columns}

        # is_enabled のデフォルトは False
        assert columns["is_enabled"].default is not None
        # rollout_percentage のデフォルトは 100.0
        assert columns["rollout_percentage"].default is not None
        # tenant_id は nullable
        assert columns["tenant_id"].nullable is True


# ── FeatureFlagService 評価ロジック テスト ─────────────────────────────────


class TestFeatureFlagEvaluation:
    """evaluate() メソッドのテスト"""

    def _make_service(self):
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        return FeatureFlagService(mock_db, redis_client=None)

    def _make_flag(self, **kwargs):
        from src.models.feature_flag import FeatureFlag

        defaults = {
            "name": "test_flag",
            "is_enabled": True,
            "rollout_percentage": 100.0,
            "tenant_id": None,
        }
        defaults.update(kwargs)
        flag = FeatureFlag()
        for k, v in defaults.items():
            setattr(flag, k, v)
        return flag

    def test_disabled_flag(self):
        """is_enabled=False のフラグは無効"""
        svc = self._make_service()
        flag = self._make_flag(is_enabled=False)
        result = svc.evaluate(flag)
        assert result.is_active is False
        assert result.reason == "disabled"

    def test_enabled_flag_full_rollout(self):
        """100% ロールアウトは常に有効"""
        svc = self._make_service()
        flag = self._make_flag(is_enabled=True, rollout_percentage=100.0)
        result = svc.evaluate(flag, user_id="user-123")
        assert result.is_active is True
        assert result.reason == "enabled"

    def test_tenant_mismatch(self):
        """テナントが一致しない場合は無効"""
        svc = self._make_service()
        tenant_id = uuid.uuid4()
        flag = self._make_flag(is_enabled=True, tenant_id=tenant_id)
        result = svc.evaluate(flag, tenant_id="other-tenant")
        assert result.is_active is False
        assert result.reason == "tenant_mismatch"

    def test_tenant_match(self):
        """テナントが一致する場合は有効"""
        svc = self._make_service()
        tenant_id = uuid.uuid4()
        flag = self._make_flag(is_enabled=True, tenant_id=tenant_id)
        result = svc.evaluate(flag, tenant_id=str(tenant_id))
        assert result.is_active is True

    def test_rollout_no_user_id(self):
        """カナリア割合 < 100% でユーザーIDなしは無効"""
        svc = self._make_service()
        flag = self._make_flag(is_enabled=True, rollout_percentage=50.0)
        result = svc.evaluate(flag, user_id=None)
        assert result.is_active is False
        assert result.reason == "rollout_no_user_id"

    def test_rollout_consistency(self):
        """同じユーザーIDは常に同じ結果（一貫性保証）"""
        svc = self._make_service()
        flag = self._make_flag(is_enabled=True, rollout_percentage=50.0)
        user_id = "user-consistent-abc123"
        results = [svc.evaluate(flag, user_id=user_id).is_active for _ in range(5)]
        assert len(set(results)) == 1  # 全て同じ結果

    def test_rollout_zero_percent_always_disabled(self):
        """0% ロールアウトは全ユーザー無効"""
        svc = self._make_service()
        flag = self._make_flag(is_enabled=True, rollout_percentage=0.0)
        for i in range(10):
            result = svc.evaluate(flag, user_id=f"user-{i}")
            assert result.is_active is False

    def test_evaluate_from_dict(self):
        """dict 形式のキャッシュデータからも評価できる"""
        svc = self._make_service()
        cached = {
            "name": "cached_flag",
            "is_enabled": True,
            "rollout_percentage": 100.0,
            "tenant_id": None,
        }
        result = svc.evaluate(cached)
        assert result.is_active is True


# ── FeatureFlagService CRUD テスト ─────────────────────────────────────────


class TestFeatureFlagServiceCrud:
    """CRUD 操作のテスト"""

    def _make_service(self):
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        return FeatureFlagService(mock_db, redis_client=None), mock_db

    def _make_flag_model(self, name="test_flag", is_enabled=False):
        from src.models.feature_flag import FeatureFlag

        flag = MagicMock(spec=FeatureFlag)
        flag.name = name
        flag.is_enabled = is_enabled
        flag.rollout_percentage = 100.0
        flag.tenant_id = None
        return flag

    @pytest.mark.asyncio
    async def test_create_flag(self):
        """フラグを新規作成できる"""
        from src.schemas.feature_flag import FeatureFlagCreate
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        svc = FeatureFlagService(mock_db)
        data = FeatureFlagCreate(name="new_feature", is_enabled=True)

        await svc.create(data, updated_by="admin")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_found(self):
        """名前でフラグを取得できる"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_flag = self._make_flag_model()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_flag
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = FeatureFlagService(mock_db)
        result = await svc.get_by_name("test_flag")
        assert result is mock_flag

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self):
        """存在しない名前は None を返す"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = FeatureFlagService(mock_db)
        result = await svc.get_by_name("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all(self):
        """全フラグ一覧を取得できる"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        flags = [self._make_flag_model(f"flag_{i}") for i in range(3)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = flags
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = FeatureFlagService(mock_db)
        result = await svc.list_all()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_update_flag(self):
        """フラグを更新できる"""
        from src.schemas.feature_flag import FeatureFlagUpdate
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_flag = self._make_flag_model()
        svc = FeatureFlagService(mock_db)
        data = FeatureFlagUpdate(is_enabled=True, rollout_percentage=75.0)

        await svc.update(mock_flag, data, updated_by="admin")

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_flag(self):
        """フラグを削除できる"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_flag = self._make_flag_model()
        svc = FeatureFlagService(mock_db)

        await svc.delete(mock_flag)

        mock_db.delete.assert_called_once_with(mock_flag)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_toggle_enable(self):
        """無効→有効に切り替えられる"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_flag = self._make_flag_model(is_enabled=False)
        svc = FeatureFlagService(mock_db)

        await svc.toggle(mock_flag, updated_by="admin")

        assert mock_flag.is_enabled is True

    @pytest.mark.asyncio
    async def test_toggle_disable(self):
        """有効→無効に切り替えられる"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_flag = self._make_flag_model(is_enabled=True)
        svc = FeatureFlagService(mock_db)

        await svc.toggle(mock_flag)

        assert mock_flag.is_enabled is False


# ── is_active キャッシュ テスト ───────────────────────────────────────────


class TestFeatureFlagIsActive:
    """is_active() メソッドのキャッシュ動作テスト"""

    @pytest.mark.asyncio
    async def test_is_active_from_cache(self):
        """キャッシュヒット時はキャッシュから評価する"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        import json

        mock_redis.get = AsyncMock(
            return_value=json.dumps(
                {"is_enabled": True, "rollout_percentage": 100.0, "tenant_id": None}
            ).encode()
        )
        mock_redis.setex = AsyncMock()

        svc = FeatureFlagService(mock_db, redis_client=mock_redis)
        result = await svc.is_active("cached_flag")

        assert result is True
        mock_db.execute.assert_not_called()  # DB は参照しない

    @pytest.mark.asyncio
    async def test_is_active_db_fallback(self):
        """キャッシュミス時は DB から取得する"""
        from src.models.feature_flag import FeatureFlag
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        flag = MagicMock(spec=FeatureFlag)
        flag.name = "db_flag"
        flag.is_enabled = True
        flag.rollout_percentage = 100.0
        flag.tenant_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = flag
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = FeatureFlagService(mock_db, redis_client=mock_redis)
        result = await svc.is_active("db_flag")

        assert result is True
        mock_redis.setex.assert_called_once()  # キャッシュに保存された

    @pytest.mark.asyncio
    async def test_is_active_flag_not_found(self):
        """フラグが存在しない場合は False"""
        from src.services.feature_flag_service import FeatureFlagService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = FeatureFlagService(mock_db, redis_client=None)
        result = await svc.is_active("nonexistent_flag")

        assert result is False


# ── Alembicマイグレーション テスト ────────────────────────────────────────


class TestFeatureFlagMigration:
    """マイグレーションファイル検証"""

    def test_migration_file_exists(self):
        """マイグレーションファイルが存在する"""
        import os

        path = "alembic/versions/021_add_feature_flags.py"
        assert os.path.exists(path), f"マイグレーションファイルが見つかりません: {path}"

    def test_migration_revision(self):
        """リビジョンが正しい"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_021",
            "alembic/versions/021_add_feature_flags.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        assert migration.revision == "021"
        assert migration.down_revision == "020"

    def test_migration_has_upgrade(self):
        """upgrade 関数が存在する"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_021",
            "alembic/versions/021_add_feature_flags.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        assert callable(migration.upgrade)

    def test_migration_has_downgrade(self):
        """downgrade 関数が存在する"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_021",
            "alembic/versions/021_add_feature_flags.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        assert callable(migration.downgrade)
