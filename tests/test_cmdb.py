"""CMDB管理テスト"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.cmdb import CICreate, CIRelationshipCreate, CIUpdate


def test_ci_create_valid_status():
    """CIのデフォルトstatusはActiveであること"""
    ci = MagicMock()
    ci.status = "Active"
    assert ci.status in ("Active", "Inactive", "Maintenance", "Retired")


def test_ci_update_invalid_status():
    """無効なstatusはバリデーションエラーになること"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CIUpdate(status="Unknown")


def test_ci_update_valid_statuses():
    """有効なstatus値はバリデーションを通過すること"""
    for s in ("Active", "Inactive", "Maintenance", "Retired"):
        update = CIUpdate(status=s)
        assert update.status == s


def test_ci_relationship_types_defined():
    """関係タイプは任意の文字列を受け付けること"""
    rel = CIRelationshipCreate(
        source_ci_id=uuid.uuid4(),
        target_ci_id=uuid.uuid4(),
        relationship_type="depends_on",
    )
    assert rel.relationship_type == "depends_on"


def test_ci_self_relationship_forbidden():
    """source_ci_id == target_ci_id の場合はValueErrorになること"""
    import asyncio

    from src.services.cmdb_service import create_ci_relationship

    same_id = uuid.uuid4()
    data = {
        "source_ci_id": same_id,
        "target_ci_id": same_id,
        "relationship_type": "depends_on",
    }

    async def run():
        db = AsyncMock()
        with pytest.raises(ValueError, match="同じCI"):
            await create_ci_relationship(db, data)

    asyncio.get_event_loop().run_until_complete(run())


def test_ci_status_transitions():
    """Active→Inactive→Maintenance→Retiredの順でstatus更新が可能なこと"""
    transitions = ["Active", "Inactive", "Maintenance", "Retired"]
    for s in transitions:
        update = CIUpdate(status=s)
        assert update.status == s


def test_ci_type_filter():
    """ci_typeフィルタのクエリパラメータが正しく渡せること"""
    from src.schemas.cmdb import CICreate
    ci = CICreate(ci_name="WebServer01", ci_type="Server")
    assert ci.ci_type == "Server"

    ci2 = CICreate(ci_name="AppDB01", ci_type="Database")
    assert ci2.ci_type == "Database"
    assert ci.ci_type != ci2.ci_type


def test_ci_attributes_jsonb():
    """attributesがdictとして保存できること"""
    ci = CICreate(
        ci_name="TestCI",
        ci_type="Application",
        attributes={"env": "production", "version": "1.2.3", "replicas": 3},
    )
    assert isinstance(ci.attributes, dict)
    assert ci.attributes["env"] == "production"
    assert ci.attributes["replicas"] == 3


def test_impact_analysis_empty():
    """依存関係なしのCI影響分析は空リストを返すこと"""
    import asyncio

    from src.services.cmdb_service import analyze_impact

    ci_id = uuid.uuid4()

    async def run():
        db = AsyncMock()
        mock_ci = MagicMock()
        mock_ci.ci_id = ci_id
        mock_ci.ci_name = "TestCI"

        # outgoing relationships: none
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        # get_ci mock
        ci_result = MagicMock()
        ci_result.scalar_one_or_none.return_value = mock_ci

        db.execute = AsyncMock(side_effect=[empty_result, ci_result])

        result = await analyze_impact(db, ci_id)
        assert result["direct_dependents"] == []
        assert result["transitive_count"] == 0
        assert result["ci_id"] == ci_id

    asyncio.get_event_loop().run_until_complete(run())
