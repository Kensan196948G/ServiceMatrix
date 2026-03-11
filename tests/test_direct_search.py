"""search.py エンドポイント直接呼び出しテスト - カバレッジ向上

ASGI TestClient ではasync関数ボディが追跡されないため、
直接呼び出しパターンで全分岐をカバーする。

対象: src/api/v1/search.py
カバー対象行: 28-121 (全関数ボディ)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_incident_mock(title="テストインシデント"):
    inc = MagicMock()
    inc.incident_id = uuid.uuid4()
    inc.title = title
    inc.status = "Open"
    return inc


def _make_problem_mock(title="テスト問題"):
    prob = MagicMock()
    prob.problem_id = uuid.uuid4()
    prob.title = title
    prob.status = "New"
    return prob


def _make_change_mock(title="テスト変更"):
    chg = MagicMock()
    chg.change_id = uuid.uuid4()
    chg.title = title
    chg.status = "Draft"
    return chg


def _make_ci_mock(ci_name="テストCI"):
    ci = MagicMock()
    ci.ci_id = uuid.uuid4()
    ci.ci_name = ci_name
    ci.ci_type = "Server"
    return ci


def _make_execute_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _make_db(*execute_results):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=list(execute_results))
    return db


# ─── 全リソースタイプ検索 ─────────────────────────────────────────────────────


async def test_global_search_all_types():
    """全4リソースタイプ（incidents/problems/changes/cmdb）を検索"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    inc = _make_incident_mock("障害テスト")
    prob = _make_problem_mock("問題テスト")
    chg = _make_change_mock("変更テスト")
    ci = _make_ci_mock("CIテスト")

    db = _make_db(
        _make_execute_result([inc]),
        _make_execute_result([prob]),
        _make_execute_result([chg]),
        _make_execute_result([ci]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="テスト", types=None, limit=5
    )

    assert result["query"] == "テスト"
    assert result["total"] == 4
    assert len(result["results"]["incidents"]) == 1
    assert len(result["results"]["problems"]) == 1
    assert len(result["results"]["changes"]) == 1
    assert len(result["results"]["cmdb"]) == 1


async def test_global_search_incidents_result_fields():
    """incidents 結果オブジェクトが id/title/status/type を持つ"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    inc = _make_incident_mock("障害テスト")

    db = _make_db(
        _make_execute_result([inc]),
        _make_execute_result([]),
        _make_execute_result([]),
        _make_execute_result([]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="障害テスト", types=None, limit=5
    )

    inc_result = result["results"]["incidents"][0]
    assert "id" in inc_result
    assert inc_result["title"] == "障害テスト"
    assert inc_result["status"] == "Open"
    assert inc_result["type"] == "incident"


async def test_global_search_problems_result_fields():
    """problems 結果が id/title/status/type を持つ"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    prob = _make_problem_mock("ネットワーク問題")

    db = _make_db(
        _make_execute_result([]),
        _make_execute_result([prob]),
        _make_execute_result([]),
        _make_execute_result([]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="ネットワーク", types=None, limit=5
    )

    prob_result = result["results"]["problems"][0]
    assert prob_result["title"] == "ネットワーク問題"
    assert prob_result["type"] == "problem"


async def test_global_search_changes_result_fields():
    """changes 結果が id/title/status/type を持つ"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    chg = _make_change_mock("システム変更")

    db = _make_db(
        _make_execute_result([]),
        _make_execute_result([]),
        _make_execute_result([chg]),
        _make_execute_result([]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="システム", types=None, limit=5
    )

    chg_result = result["results"]["changes"][0]
    assert chg_result["title"] == "システム変更"
    assert chg_result["type"] == "change"


async def test_global_search_cmdb_result_fields():
    """cmdb 結果が id/title/ci_type/type を持つ"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    ci = _make_ci_mock("本番サーバー")

    db = _make_db(
        _make_execute_result([]),
        _make_execute_result([]),
        _make_execute_result([]),
        _make_execute_result([ci]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="本番", types=None, limit=5
    )

    ci_result = result["results"]["cmdb"][0]
    assert ci_result["title"] == "本番サーバー"
    assert ci_result["ci_type"] == "Server"
    assert ci_result["type"] == "cmdb"


# ─── types フィルタ分岐 ────────────────────────────────────────────────────────


async def test_global_search_incidents_only():
    """types=incidents → incidents のみ検索"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    inc = _make_incident_mock("障害のみ")

    db = _make_db(_make_execute_result([inc]))

    result = await global_search(
        db=db, current_user=mock_user, q="障害", types="incidents", limit=5
    )

    assert "incidents" in result["results"]
    assert "problems" not in result["results"]
    assert "changes" not in result["results"]
    assert "cmdb" not in result["results"]
    assert result["total"] == 1


async def test_global_search_problems_only():
    """types=problems → problems のみ検索"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    prob = _make_problem_mock("問題のみ")

    db = _make_db(_make_execute_result([prob]))

    result = await global_search(
        db=db, current_user=mock_user, q="問題", types="problems", limit=5
    )

    assert "problems" in result["results"]
    assert "incidents" not in result["results"]
    assert result["total"] == 1


async def test_global_search_changes_only():
    """types=changes → changes のみ検索"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    chg = _make_change_mock("変更のみ")

    db = _make_db(_make_execute_result([chg]))

    result = await global_search(
        db=db, current_user=mock_user, q="変更", types="changes", limit=5
    )

    assert "changes" in result["results"]
    assert "incidents" not in result["results"]
    assert result["total"] == 1


async def test_global_search_cmdb_only():
    """types=cmdb → cmdb のみ検索"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()
    ci = _make_ci_mock("CMDBのみ")

    db = _make_db(_make_execute_result([ci]))

    result = await global_search(
        db=db, current_user=mock_user, q="CMDB", types="cmdb", limit=5
    )

    assert "cmdb" in result["results"]
    assert "incidents" not in result["results"]
    assert result["total"] == 1


async def test_global_search_multiple_types():
    """types=incidents,changes → 2種のみ検索"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()

    db = _make_db(
        _make_execute_result([_make_incident_mock()]),
        _make_execute_result([_make_change_mock()]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="テスト", types="incidents,changes", limit=5
    )

    assert "incidents" in result["results"]
    assert "changes" in result["results"]
    assert "problems" not in result["results"]
    assert result["total"] == 2


# ─── 空結果ケース ─────────────────────────────────────────────────────────────


async def test_global_search_empty_results():
    """検索結果なし → total=0"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()

    db = _make_db(
        _make_execute_result([]),
        _make_execute_result([]),
        _make_execute_result([]),
        _make_execute_result([]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="存在しない", types=None, limit=5
    )

    assert result["total"] == 0
    for key in ("incidents", "problems", "changes", "cmdb"):
        assert result["results"][key] == []


async def test_global_search_total_calculation():
    """total = 全リソースタイプの合計数"""
    from src.api.v1.search import global_search

    mock_user = MagicMock()

    db = _make_db(
        _make_execute_result([_make_incident_mock(), _make_incident_mock()]),
        _make_execute_result([_make_problem_mock()]),
        _make_execute_result([]),
        _make_execute_result([_make_ci_mock(), _make_ci_mock(), _make_ci_mock()]),
    )

    result = await global_search(
        db=db, current_user=mock_user, q="テスト", types=None, limit=10
    )

    assert result["total"] == 6  # 2 + 1 + 0 + 3
