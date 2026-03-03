"""CMDBグラフAPIエンドポイント関数の直接呼び出しユニットテスト

エンドポイント関数を直接awaitして呼び出す方式でカバレッジを取得する。
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.cmdb import (
    batch_impact,
    get_ci_graph,
    get_graph,
    get_upstream_cis,
)
from src.models.cmdb import CIRelationship, ConfigurationItem
from src.models.user import User, UserRole
from src.schemas.cmdb import BatchImpactRequest

pytestmark = pytest.mark.asyncio

NOW = datetime.now(UTC)


def _make_user(**overrides):
    defaults = {
        "user_id": uuid.uuid4(),
        "username": "testadmin",
        "email": "admin@test.com",
        "role": UserRole.SYSTEM_ADMIN,
        "is_active": True,
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_ci(**overrides):
    defaults = {
        "ci_id": uuid.uuid4(),
        "ci_name": "TestServer",
        "ci_type": "Server",
        "ci_class": "Physical",
        "status": "Active",
        "version": "1.0",
        "owner_id": None,
        "description": "テスト用CI",
        "attributes": {"env": "test"},
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    ci = MagicMock(spec=ConfigurationItem)
    for k, v in defaults.items():
        setattr(ci, k, v)
    return ci


def _make_relationship(source_id, target_id, **overrides):
    defaults = {
        "relationship_id": uuid.uuid4(),
        "source_ci_id": source_id,
        "target_ci_id": target_id,
        "relationship_type": "depends_on",
        "description": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    rel = MagicMock(spec=CIRelationship)
    for k, v in defaults.items():
        setattr(rel, k, v)
    return rel


# ========================================================================
# GET /api/v1/cmdb/graph
# ========================================================================


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_graph_returns_empty(mock_svc):
    """空のグラフを返す"""
    mock_svc.get_graph = AsyncMock(
        return_value={
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
        }
    )
    result = await get_graph(
        db=AsyncMock(), current_user=_make_user(), ci_type=None, status_filter=None
    )
    assert result["total_nodes"] == 0
    assert result["total_edges"] == 0
    mock_svc.get_graph.assert_awaited_once()


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_graph_with_nodes_and_edges(mock_svc):
    """ノードとエッジを含むグラフを返す"""
    ci1_id = uuid.uuid4()
    ci2_id = uuid.uuid4()
    mock_svc.get_graph = AsyncMock(
        return_value={
            "nodes": [
                {
                    "id": str(ci1_id),
                    "label": "App1",
                    "ci_type": "Application",
                    "status": "Active",
                    "attributes": None,
                },
                {
                    "id": str(ci2_id),
                    "label": "DB1",
                    "ci_type": "Database",
                    "status": "Active",
                    "attributes": None,
                },
            ],
            "edges": [
                {
                    "id": str(uuid.uuid4()),
                    "source": str(ci1_id),
                    "target": str(ci2_id),
                    "relationship_type": "depends_on",
                }
            ],
            "total_nodes": 2,
            "total_edges": 1,
        }
    )
    result = await get_graph(
        db=AsyncMock(), current_user=_make_user(), ci_type=None, status_filter=None
    )
    assert result["total_nodes"] == 2
    assert result["total_edges"] == 1
    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_graph_with_ci_type_filter(mock_svc):
    """ci_typeフィルタ付きグラフ取得"""
    mock_svc.get_graph = AsyncMock(
        return_value={"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}
    )
    db = AsyncMock()
    await get_graph(
        db=db,
        current_user=_make_user(),
        ci_type="Server",
        status_filter=None,
    )
    mock_svc.get_graph.assert_awaited_once_with(db, ci_type="Server", status=None)


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_graph_with_status_filter(mock_svc):
    """statusフィルタ付きグラフ取得"""
    mock_svc.get_graph = AsyncMock(
        return_value={"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}
    )
    db = AsyncMock()
    await get_graph(
        db=db,
        current_user=_make_user(),
        ci_type=None,
        status_filter="Active",
    )
    mock_svc.get_graph.assert_awaited_once_with(db, ci_type=None, status="Active")


# ========================================================================
# GET /api/v1/cmdb/cis/{ci_id}/graph
# ========================================================================


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_ci_graph_success(mock_svc):
    """特定CI起点のグラフ取得成功"""
    ci_id = uuid.uuid4()
    ci = _make_ci(ci_id=ci_id)
    mock_svc.get_ci = AsyncMock(return_value=ci)
    mock_svc.get_ci_graph = AsyncMock(
        return_value={
            "nodes": [
                {
                    "id": str(ci_id),
                    "label": ci.ci_name,
                    "ci_type": ci.ci_type,
                    "status": ci.status,
                    "attributes": ci.attributes,
                }
            ],
            "edges": [],
            "total_nodes": 1,
            "total_edges": 0,
        }
    )
    result = await get_ci_graph(ci_id=ci_id, db=AsyncMock(), current_user=_make_user(), depth=3)
    assert result["total_nodes"] == 1
    assert result["nodes"][0]["id"] == str(ci_id)


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_ci_graph_not_found(mock_svc):
    """存在しないCI起点のグラフ取得で404"""
    mock_svc.get_ci = AsyncMock(return_value=None)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_ci_graph(ci_id=uuid.uuid4(), db=AsyncMock(), current_user=_make_user(), depth=3)
    assert exc_info.value.status_code == 404


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_ci_graph_custom_depth(mock_svc):
    """depth指定でCI起点グラフ取得"""
    ci_id = uuid.uuid4()
    mock_svc.get_ci = AsyncMock(return_value=_make_ci(ci_id=ci_id))
    mock_svc.get_ci_graph = AsyncMock(
        return_value={
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
        }
    )
    await get_ci_graph(ci_id=ci_id, db=AsyncMock(), current_user=_make_user(), depth=1)
    mock_svc.get_ci_graph.assert_awaited_once()
    call_args = mock_svc.get_ci_graph.call_args
    assert call_args.kwargs["depth"] == 1


# ========================================================================
# GET /api/v1/cmdb/cis/{ci_id}/upstream
# ========================================================================


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_upstream_cis_success(mock_svc):
    """上流CI取得成功"""
    ci_id = uuid.uuid4()
    upstream_ci = _make_ci(ci_name="UpstreamApp")
    mock_svc.get_ci = AsyncMock(return_value=_make_ci(ci_id=ci_id))
    mock_svc.get_upstream_cis = AsyncMock(return_value=[upstream_ci])
    result = await get_upstream_cis(ci_id=ci_id, db=AsyncMock(), current_user=_make_user())
    assert len(result) == 1


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_upstream_cis_not_found(mock_svc):
    """存在しないCIの上流取得で404"""
    mock_svc.get_ci = AsyncMock(return_value=None)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_upstream_cis(ci_id=uuid.uuid4(), db=AsyncMock(), current_user=_make_user())
    assert exc_info.value.status_code == 404


@patch("src.api.v1.cmdb.cmdb_service")
async def test_get_upstream_cis_empty(mock_svc):
    """上流CIが存在しない場合空リストを返す"""
    ci_id = uuid.uuid4()
    mock_svc.get_ci = AsyncMock(return_value=_make_ci(ci_id=ci_id))
    mock_svc.get_upstream_cis = AsyncMock(return_value=[])
    result = await get_upstream_cis(ci_id=ci_id, db=AsyncMock(), current_user=_make_user())
    assert result == []


# ========================================================================
# POST /api/v1/cmdb/batch-impact
# ========================================================================


@patch("src.api.v1.cmdb.cmdb_service")
async def test_batch_impact_single_ci(mock_svc):
    """単一CIのバッチ影響分析"""
    ci_id = uuid.uuid4()
    mock_svc.batch_impact_analysis = AsyncMock(
        return_value={
            "items": [
                {
                    "ci_id": ci_id,
                    "ci_name": "App1",
                    "direct_dependents": [],
                    "transitive_count": 0,
                }
            ],
            "total_affected": 0,
        }
    )
    req = BatchImpactRequest(ci_ids=[ci_id])
    result = await batch_impact(data=req, db=AsyncMock(), current_user=_make_user())
    assert len(result["items"]) == 1
    assert result["total_affected"] == 0


@patch("src.api.v1.cmdb.cmdb_service")
async def test_batch_impact_multiple_cis(mock_svc):
    """複数CIのバッチ影響分析"""
    ci1_id = uuid.uuid4()
    ci2_id = uuid.uuid4()
    dep_ci = _make_ci(ci_name="SharedDB")
    mock_svc.batch_impact_analysis = AsyncMock(
        return_value={
            "items": [
                {
                    "ci_id": ci1_id,
                    "ci_name": "App1",
                    "direct_dependents": [dep_ci],
                    "transitive_count": 1,
                },
                {
                    "ci_id": ci2_id,
                    "ci_name": "App2",
                    "direct_dependents": [dep_ci],
                    "transitive_count": 1,
                },
            ],
            "total_affected": 1,
        }
    )
    req = BatchImpactRequest(ci_ids=[ci1_id, ci2_id])
    result = await batch_impact(data=req, db=AsyncMock(), current_user=_make_user())
    assert len(result["items"]) == 2
    assert result["total_affected"] == 1


# ========================================================================
# サービス層テスト（get_graph, get_ci_graph, get_upstream_cis, batch_impact_analysis）
# ========================================================================


async def test_service_get_graph():
    """cmdb_service.get_graph のユニットテスト"""
    from src.services.cmdb_service import get_graph as svc_get_graph

    ci1 = _make_ci(ci_id=uuid.uuid4(), ci_name="Web", ci_type="Application")
    ci2 = _make_ci(ci_id=uuid.uuid4(), ci_name="DB", ci_type="Database")
    rel = _make_relationship(ci1.ci_id, ci2.ci_id)

    db = AsyncMock()
    # 1回目: CI一覧取得、2回目: Relationship一覧取得
    ci_result = MagicMock()
    ci_result.scalars.return_value.all.return_value = [ci1, ci2]
    rel_result = MagicMock()
    rel_result.scalars.return_value.all.return_value = [rel]
    db.execute = AsyncMock(side_effect=[ci_result, rel_result])

    result = await svc_get_graph(db)
    assert result["total_nodes"] == 2
    assert result["total_edges"] == 1
    assert result["nodes"][0]["label"] == "Web"


async def test_service_get_graph_filtered():
    """cmdb_service.get_graph ci_typeフィルタ適用"""
    from src.services.cmdb_service import get_graph as svc_get_graph

    ci1 = _make_ci(ci_id=uuid.uuid4(), ci_type="Server")

    db = AsyncMock()
    ci_result = MagicMock()
    ci_result.scalars.return_value.all.return_value = [ci1]
    rel_result = MagicMock()
    rel_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[ci_result, rel_result])

    result = await svc_get_graph(db, ci_type="Server")
    assert result["total_nodes"] == 1
    assert result["total_edges"] == 0


async def test_service_get_upstream_cis():
    """cmdb_service.get_upstream_cis のユニットテスト"""
    from src.services.cmdb_service import get_upstream_cis as svc_upstream

    ci_id = uuid.uuid4()
    upstream_id = uuid.uuid4()
    rel = _make_relationship(upstream_id, ci_id)
    upstream_ci = _make_ci(ci_id=upstream_id, ci_name="Upstream")

    db = AsyncMock()
    # 1回目: incoming relationship取得
    rel_result = MagicMock()
    rel_result.scalars.return_value.all.return_value = [rel]
    # 2回目: get_ci でupstream_ciを返す
    ci_result = MagicMock()
    ci_result.scalar_one_or_none.return_value = upstream_ci
    db.execute = AsyncMock(side_effect=[rel_result, ci_result])

    result = await svc_upstream(db, ci_id)
    assert len(result) == 1
    assert result[0].ci_name == "Upstream"


async def test_service_get_ci_graph_single_node():
    """cmdb_service.get_ci_graph 単一ノード（関係なし）"""
    from src.services.cmdb_service import get_ci_graph as svc_ci_graph

    ci_id = uuid.uuid4()
    ci = _make_ci(ci_id=ci_id, ci_name="Standalone")

    db = AsyncMock()
    # BFS: 初回クエリで関係なし
    empty_rel = MagicMock()
    empty_rel.scalars.return_value.all.return_value = []
    # get_ci でノード情報取得
    ci_result = MagicMock()
    ci_result.scalar_one_or_none.return_value = ci
    db.execute = AsyncMock(side_effect=[empty_rel, ci_result])

    result = await svc_ci_graph(db, ci_id, depth=3)
    assert result["total_nodes"] == 1
    assert result["total_edges"] == 0
    assert result["nodes"][0]["label"] == "Standalone"


async def test_service_batch_impact_analysis():
    """cmdb_service.batch_impact_analysis のユニットテスト"""
    from src.services.cmdb_service import batch_impact_analysis as svc_batch

    ci1_id = uuid.uuid4()
    ci2_id = uuid.uuid4()
    dep_id = uuid.uuid4()

    ci1 = _make_ci(ci_id=ci1_id, ci_name="App1")
    dep = _make_ci(ci_id=dep_id, ci_name="SharedDB")
    rel1 = _make_relationship(ci1_id, dep_id)

    db = AsyncMock()

    # analyze_impact(ci1_id): outgoing取得 → get_ci(dep) → BFS → get_ci(ci1)
    # analyze_impact(ci2_id): outgoing取得(空) → get_ci(ci2)
    # _collect_transitive_ids(ci1_id): outgoing取得
    # _collect_transitive_ids(ci2_id): outgoing取得(空)
    rel_result_with_dep = MagicMock()
    rel_result_with_dep.scalars.return_value.all.return_value = [rel1]
    empty_rel = MagicMock()
    empty_rel.scalars.return_value.all.return_value = []
    ci1_result = MagicMock()
    ci1_result.scalar_one_or_none.return_value = ci1
    dep_result = MagicMock()
    dep_result.scalar_one_or_none.return_value = dep
    ci2 = _make_ci(ci_id=ci2_id, ci_name="App2")
    ci2_result = MagicMock()
    ci2_result.scalar_one_or_none.return_value = ci2

    # 呼び出し順序:
    # analyze_impact(ci1): select outgoing(ci1) -> [rel1]
    # get_ci(dep_id) -> dep
    # BFS: select outgoing(dep_id) -> []
    # get_ci(ci1_id) -> ci1
    # analyze_impact(ci2): select outgoing(ci2) -> []
    # get_ci(ci2_id) -> ci2
    # _collect_transitive(ci1): select outgoing(ci1) -> [rel1]
    # BFS: select outgoing(dep_id) -> []
    # _collect_transitive(ci2): select outgoing(ci2) -> []
    db.execute = AsyncMock(
        side_effect=[
            rel_result_with_dep,  # analyze_impact(ci1): outgoing
            dep_result,  # get_ci(dep_id)
            empty_rel,  # BFS from dep_id
            ci1_result,  # get_ci(ci1_id)
            empty_rel,  # analyze_impact(ci2): outgoing
            ci2_result,  # get_ci(ci2_id)
            rel_result_with_dep,  # _collect_transitive(ci1): outgoing
            empty_rel,  # BFS from dep_id
            empty_rel,  # _collect_transitive(ci2): outgoing
        ]
    )

    result = await svc_batch(db, [ci1_id, ci2_id])
    assert len(result["items"]) == 2
    assert result["total_affected"] == 1  # dep_idのみ


# ========================================================================
# スキーマバリデーションテスト
# ========================================================================


def test_batch_impact_request_min_length():
    """BatchImpactRequest ci_ids最小長バリデーション"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BatchImpactRequest(ci_ids=[])


def test_batch_impact_request_max_length():
    """BatchImpactRequest ci_ids最大長バリデーション"""
    from pydantic import ValidationError

    ids = [uuid.uuid4() for _ in range(21)]
    with pytest.raises(ValidationError):
        BatchImpactRequest(ci_ids=ids)


def test_batch_impact_request_valid():
    """BatchImpactRequest 正常なリクエスト"""
    ids = [uuid.uuid4() for _ in range(5)]
    req = BatchImpactRequest(ci_ids=ids)
    assert len(req.ci_ids) == 5


def test_graph_response_schema():
    """GraphResponse スキーマ構築テスト"""
    from src.schemas.cmdb import GraphEdge, GraphNode, GraphResponse

    node = GraphNode(id="abc", label="TestNode", ci_type="Server", status="Active", attributes=None)
    edge = GraphEdge(id="edge1", source="abc", target="def", relationship_type="depends_on")
    resp = GraphResponse(nodes=[node], edges=[edge], total_nodes=1, total_edges=1)
    assert resp.total_nodes == 1
    assert resp.edges[0].relationship_type == "depends_on"
