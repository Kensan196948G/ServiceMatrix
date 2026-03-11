"""cmdb_service.py サービス層直接テスト - カバレッジ向上

対象: src/services/cmdb_service.py
カバー対象行: 20-29, 42, 44, 46, 49-53, 65-81, 91-97, 109, 119-121, 126-133
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_ci_mock(ci_id=None, ci_name="テストCI", ci_type="Server", status="Active"):
    ci = MagicMock()
    ci.ci_id = ci_id or uuid.uuid4()
    ci.ci_name = ci_name
    ci.ci_type = ci_type
    ci.status = status
    ci.version = "1.0"
    return ci


def _make_rel_mock(source_id=None, target_id=None, rel_type="depends_on"):
    rel = MagicMock()
    rel.relationship_id = uuid.uuid4()
    rel.source_ci_id = source_id or uuid.uuid4()
    rel.target_ci_id = target_id or uuid.uuid4()
    rel.relationship_type = rel_type
    return rel


_MISSING = object()  # sentinel: None との区別のため


def _make_execute_result(scalar_one_or_none=_MISSING, scalars_all=_MISSING, scalar_one=_MISSING):
    """db.execute() の返り値モックを生成"""
    result = MagicMock()
    if scalar_one_or_none is not _MISSING:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    if scalars_all is not _MISSING:
        result.scalars.return_value.all.return_value = scalars_all
    if scalar_one is not _MISSING:
        result.scalar_one.return_value = scalar_one
    return result


# ─── create_ci ───────────────────────────────────────────────────────────────


async def test_create_ci_service_success():
    """create_ci: audit_log + logger.info + return をカバー（lines 20-29）"""
    from src.services.cmdb_service import create_ci

    db = AsyncMock()
    ci_id = uuid.uuid4()

    ci_instance = MagicMock()
    ci_instance.ci_id = ci_id
    ci_instance.ci_name = "テストCI"
    ci_instance.ci_type = "Server"

    with patch("src.services.cmdb_service.ConfigurationItem", return_value=ci_instance):
        with patch(
            "src.services.cmdb_service.audit_service.record_audit_log",
            new=AsyncMock(return_value=None),
        ):
            result = await create_ci(db, {"ci_name": "テストCI", "ci_type": "Server"})

    db.add.assert_called_once_with(ci_instance)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(ci_instance)
    assert result is ci_instance


async def test_create_ci_service_calls_audit():
    """create_ci: audit_service が正しいアクションで呼ばれる"""
    from src.services.cmdb_service import create_ci

    db = AsyncMock()
    ci_instance = _make_ci_mock(ci_name="監査テストCI", ci_type="Database")

    with patch("src.services.cmdb_service.ConfigurationItem", return_value=ci_instance):
        with patch(
            "src.services.cmdb_service.audit_service.record_audit_log",
            new=AsyncMock(return_value=None),
        ) as mock_audit:
            await create_ci(db, {"ci_name": "監査テストCI", "ci_type": "Database"})

    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "CI_CREATE"
    assert call_kwargs["resource_type"] == "ConfigurationItem"


# ─── get_cis (フィルタカバレッジ) ────────────────────────────────────────────


async def test_get_cis_no_filters():
    """get_cis: フィルタなし → lines 49-53"""
    from src.services.cmdb_service import get_cis

    db = AsyncMock()
    ci = _make_ci_mock()

    total_result = _make_execute_result(scalar_one=0)
    items_result = _make_execute_result(scalars_all=[])
    db.execute = AsyncMock(side_effect=[total_result, items_result])

    result, total = await get_cis(db, ci_type=None, status=None, skip=0, limit=10)
    assert total == 0
    assert result == []


async def test_get_cis_with_ci_type_filter():
    """get_cis: ci_type フィルタ → line 42"""
    from src.services.cmdb_service import get_cis

    db = AsyncMock()
    ci = _make_ci_mock(ci_type="Server")

    total_result = _make_execute_result(scalar_one=1)
    items_result = _make_execute_result(scalars_all=[ci])
    db.execute = AsyncMock(side_effect=[total_result, items_result])

    result, total = await get_cis(db, ci_type="Server", status=None, skip=0, limit=10)
    assert total == 1
    assert result[0].ci_type == "Server"


async def test_get_cis_with_status_filter():
    """get_cis: status フィルタ → line 44"""
    from src.services.cmdb_service import get_cis

    db = AsyncMock()
    ci = _make_ci_mock(status="Active")

    total_result = _make_execute_result(scalar_one=1)
    items_result = _make_execute_result(scalars_all=[ci])
    db.execute = AsyncMock(side_effect=[total_result, items_result])

    result, total = await get_cis(db, ci_type=None, status="Active", skip=0, limit=10)
    assert total == 1


async def test_get_cis_with_department_filter():
    """get_cis: department フィルタ → line 46"""
    from src.services.cmdb_service import get_cis

    db = AsyncMock()
    ci = _make_ci_mock()

    total_result = _make_execute_result(scalar_one=1)
    items_result = _make_execute_result(scalars_all=[ci])
    db.execute = AsyncMock(side_effect=[total_result, items_result])

    result, total = await get_cis(
        db, ci_type=None, status=None, skip=0, limit=10, department="IT部門"
    )
    assert total == 1


async def test_get_cis_all_filters():
    """get_cis: 全フィルタ適用 → lines 42, 44, 46"""
    from src.services.cmdb_service import get_cis

    db = AsyncMock()
    ci = _make_ci_mock(ci_type="Server", status="Active")

    total_result = _make_execute_result(scalar_one=2)
    items_result = _make_execute_result(scalars_all=[ci, ci])
    db.execute = AsyncMock(side_effect=[total_result, items_result])

    result, total = await get_cis(
        db, ci_type="Server", status="Active", skip=0, limit=20, department="営業部"
    )
    assert total == 2
    assert len(result) == 2


# ─── update_ci ────────────────────────────────────────────────────────────────


async def test_update_ci_service_success():
    """update_ci: CI存在 → setattr + flush + refresh + audit_log (lines 65-81)"""
    from src.services.cmdb_service import update_ci

    db = AsyncMock()
    ci = _make_ci_mock(status="Active", ci_name="更新CI")
    ci.version = "1.0"

    get_result = _make_execute_result(scalar_one_or_none=ci)
    db.execute = AsyncMock(return_value=get_result)

    with patch(
        "src.services.cmdb_service.audit_service.record_audit_log",
        new=AsyncMock(return_value=None),
    ) as mock_audit:
        result = await update_ci(db, ci.ci_id, {"status": "Maintenance", "version": "2.0"})

    assert result is ci
    assert ci.status == "Maintenance"
    assert ci.version == "2.0"
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(ci)
    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "CI_UPDATE"


async def test_update_ci_service_not_found():
    """update_ci: CI不存在 → None返却 (early return at line 66)"""
    from src.services.cmdb_service import update_ci

    db = AsyncMock()
    get_result = _make_execute_result(scalar_one_or_none=None)
    db.execute = AsyncMock(return_value=get_result)

    result = await update_ci(db, uuid.uuid4(), {"status": "Maintenance"})
    assert result is None


# ─── create_ci_relationship (success path) ────────────────────────────────────


async def test_create_ci_relationship_service_success():
    """create_ci_relationship: 正常作成 → flush + refresh + logger.info (lines 91-97)"""
    from src.services.cmdb_service import create_ci_relationship

    db = AsyncMock()
    src_id = uuid.uuid4()
    tgt_id = uuid.uuid4()

    rel_instance = MagicMock()
    rel_instance.relationship_id = uuid.uuid4()
    rel_instance.relationship_type = "depends_on"

    with patch("src.services.cmdb_service.CIRelationship", return_value=rel_instance):
        result = await create_ci_relationship(
            db,
            {
                "source_ci_id": src_id,
                "target_ci_id": tgt_id,
                "relationship_type": "depends_on",
            },
        )

    db.add.assert_called_once_with(rel_instance)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(rel_instance)
    assert result is rel_instance


async def test_create_ci_relationship_service_self_ref_raises():
    """create_ci_relationship: 自己参照 → ValueError (line 85-86)"""
    from src.services.cmdb_service import create_ci_relationship

    db = AsyncMock()
    same_id = uuid.uuid4()

    with pytest.raises(ValueError, match="同じCI"):
        await create_ci_relationship(
            db,
            {
                "source_ci_id": same_id,
                "target_ci_id": same_id,
                "relationship_type": "depends_on",
            },
        )


# ─── get_ci_relationships ─────────────────────────────────────────────────────


async def test_get_ci_relationships_service():
    """get_ci_relationships: DB queryとreturnをカバー (lines 101-109)"""
    from src.services.cmdb_service import get_ci_relationships

    db = AsyncMock()
    ci_id = uuid.uuid4()
    rel = _make_rel_mock(source_id=ci_id)

    result_mock = _make_execute_result(scalars_all=[rel])
    db.execute = AsyncMock(return_value=result_mock)

    results = await get_ci_relationships(db, ci_id)
    assert len(results) == 1
    assert results[0].source_ci_id == ci_id


async def test_get_ci_relationships_empty():
    """get_ci_relationships: 関係なし → 空リスト"""
    from src.services.cmdb_service import get_ci_relationships

    db = AsyncMock()
    result_mock = _make_execute_result(scalars_all=[])
    db.execute = AsyncMock(return_value=result_mock)

    results = await get_ci_relationships(db, uuid.uuid4())
    assert results == []


# ─── analyze_impact ──────────────────────────────────────────────────────────


async def test_analyze_impact_with_direct_dependents():
    """analyze_impact: 直接依存あり → direct_dependents + BFS (lines 119-133)"""
    from src.services.cmdb_service import analyze_impact

    db = AsyncMock()
    ci_id = uuid.uuid4()
    dep_id = uuid.uuid4()

    # outgoing relationships: ci_id → dep_id
    rel = _make_rel_mock(source_id=ci_id, target_id=dep_id)
    outgoing_mock = _make_execute_result(scalars_all=[rel])

    # get_ci for dep_id (direct dependent)
    dep_ci = _make_ci_mock(ci_id=dep_id, ci_name="依存CI")
    dep_result = _make_execute_result(scalar_one_or_none=dep_ci)

    # BFS: no further outgoing from dep_id
    empty_sub = _make_execute_result(scalars_all=[])

    # get_ci for root ci_id
    root_ci = _make_ci_mock(ci_id=ci_id, ci_name="ルートCI")
    root_result = _make_execute_result(scalar_one_or_none=root_ci)

    db.execute = AsyncMock(
        side_effect=[outgoing_mock, dep_result, empty_sub, root_result]
    )

    result = await analyze_impact(db, ci_id)

    assert len(result["direct_dependents"]) == 1
    assert result["direct_dependents"][0].ci_name == "依存CI"
    assert result["transitive_count"] == 1
    assert result["ci_name"] == "ルートCI"


async def test_analyze_impact_with_transitive_chain():
    """analyze_impact: 推移的依存チェーン → BFSループ (lines 126-133)"""
    from src.services.cmdb_service import analyze_impact

    db = AsyncMock()
    ci_id = uuid.uuid4()
    dep1_id = uuid.uuid4()
    dep2_id = uuid.uuid4()

    # outgoing: ci_id → dep1_id
    rel1 = _make_rel_mock(source_id=ci_id, target_id=dep1_id)
    outgoing_mock = _make_execute_result(scalars_all=[rel1])

    # get_ci for dep1
    dep1_ci = _make_ci_mock(ci_id=dep1_id, ci_name="直接依存CI")
    dep1_result = _make_execute_result(scalar_one_or_none=dep1_ci)

    # BFS iteration 1 (dep1_id): dep1 → dep2
    rel2 = _make_rel_mock(source_id=dep1_id, target_id=dep2_id)
    sub_result_1 = _make_execute_result(scalars_all=[rel2])

    # BFS iteration 2 (dep2_id): no further
    sub_result_2 = _make_execute_result(scalars_all=[])

    # get_ci for root CI
    root_ci = _make_ci_mock(ci_id=ci_id, ci_name="ルートCI")
    root_result = _make_execute_result(scalar_one_or_none=root_ci)

    db.execute = AsyncMock(
        side_effect=[outgoing_mock, dep1_result, sub_result_1, sub_result_2, root_result]
    )

    result = await analyze_impact(db, ci_id)

    assert result["transitive_count"] == 2  # dep1 + dep2
    assert result["ci_name"] == "ルートCI"
    assert len(result["direct_dependents"]) == 1


async def test_analyze_impact_ci_not_found():
    """analyze_impact: ルートCIが存在しない場合 (ci_name が空文字)"""
    from src.services.cmdb_service import analyze_impact

    db = AsyncMock()
    ci_id = uuid.uuid4()

    outgoing_mock = _make_execute_result(scalars_all=[])
    root_result = _make_execute_result(scalar_one_or_none=None)

    db.execute = AsyncMock(side_effect=[outgoing_mock, root_result])

    result = await analyze_impact(db, ci_id)

    assert result["ci_name"] == ""
    assert result["transitive_count"] == 0
    assert result["direct_dependents"] == []
