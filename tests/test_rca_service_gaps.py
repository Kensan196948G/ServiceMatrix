"""rca_service.py 未カバー行テスト

対象: src/services/rca_service.py (93%)
lines 71-76 (problem not found), 81 (description), 83 (root_cause),
137 (find_similar_incidents db.execute), 148 (_find_affected_cis db.execute)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


async def test_analyze_problem_not_found_returns_rca_result():
    """analyze_problem: problem が None → RCAResult 早期リターン（lines 71-76）"""
    from src.services.rca_service import RCAService

    svc = RCAService()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    problem_id = str(uuid.uuid4())
    result = await svc.analyze_problem(db, problem_id)

    assert "見つかりませんでした" in result.analysis_summary
    assert result.problem_id == problem_id
    assert result.candidates == []


async def test_analyze_problem_with_description_and_root_cause():
    """analyze_problem: problem.description と root_cause がある → text_parts に追加（lines 81, 83）"""
    from src.services.rca_service import RCAService

    svc = RCAService()
    db = AsyncMock()

    problem_mock = MagicMock()
    problem_mock.title = "データベース障害"
    problem_mock.description = "PostgreSQL接続タイムアウトが発生した"
    problem_mock.root_cause = "コネクションプール枯渇"

    # 1st call: select Problem
    prob_result = MagicMock()
    prob_result.scalar_one_or_none.return_value = problem_mock

    # 2nd call: find_similar_incidents (db.execute in line 137)
    inc_result = MagicMock()
    inc_result.scalars.return_value.all.return_value = []

    # 3rd call: _find_affected_cis (db.execute in line 148)
    ci_result = MagicMock()
    ci_result.scalars.return_value.all.return_value = []

    db.execute = AsyncMock(side_effect=[prob_result, inc_result, ci_result])

    result = await svc.analyze_problem(db, str(uuid.uuid4()))

    # description と root_cause が処理されて analysis_text に含まれる
    assert result is not None
    assert len(result.candidates) == 1
    # 3回の db.execute が呼ばれた（Problem取得・類似インシデント・影響CI）
    assert db.execute.call_count == 3


async def test_find_similar_incidents_with_keywords_executes_db():
    """find_similar_incidents: 3文字以上のキーワードあり → db.execute が呼ばれる（line 137）"""
    from src.services.rca_service import RCAService

    svc = RCAService()
    db = AsyncMock()

    inc_mock = MagicMock()
    inc_mock.incident_number = "INC-2026-000001"
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc_mock]
    db.execute = AsyncMock(return_value=result_mock)

    # "データベース" は3文字以上なのでキーワードとして使われる
    result = await svc.find_similar_incidents(db, "データベース障害 タイムアウト")

    db.execute.assert_called_once()
    assert len(result) == 1
    assert result[0].incident_number == "INC-2026-000001"


async def test_find_affected_cis_with_keywords_executes_db():
    """_find_affected_cis: 4文字以上のキーワードあり → db.execute が呼ばれる（line 148）"""
    from src.services.rca_service import RCAService

    svc = RCAService()
    db = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = ["web-server-01", "db-primary"]
    db.execute = AsyncMock(return_value=result_mock)

    # "PostgreSQL" と "database" と "connection" と "error" はすべて4文字以上
    result = await svc._find_affected_cis(db, "PostgreSQL database connection error")

    db.execute.assert_called_once()
    assert len(result) == 2
    assert "web-server-01" in result
    assert "db-primary" in result


async def test_find_similar_incidents_no_keywords_returns_empty():
    """find_similar_incidents: 3文字未満のみ → db.execute 呼ばれず空リスト返却（line 132-133）"""
    from src.services.rca_service import RCAService

    svc = RCAService()
    db = AsyncMock()

    result = await svc.find_similar_incidents(db, "ab cd")

    db.execute.assert_not_called()
    assert result == []


async def test_find_affected_cis_no_keywords_returns_empty():
    """_find_affected_cis: 4文字未満のみ → db.execute 呼ばれず空リスト返却（line 143-144）"""
    from src.services.rca_service import RCAService

    svc = RCAService()
    db = AsyncMock()

    result = await svc._find_affected_cis(db, "ab cd xyz")

    db.execute.assert_not_called()
    assert result == []
