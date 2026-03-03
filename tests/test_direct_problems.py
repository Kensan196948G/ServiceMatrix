"""problems.py エンドポイント関数の直接呼び出しユニットテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.problems import (
    analyze_problem_rca,
    create_problem,
    get_problem,
    list_problems,
    set_known_error,
    transition_problem_status,
    update_problem,
)
from src.models.problem import Problem
from src.models.user import User, UserRole
from src.schemas.problem import (
    KnownErrorUpdate,
    ProblemCreate,
    ProblemStatusTransition,
    ProblemUpdate,
)

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


def _make_problem(**overrides):
    defaults = {
        "problem_id": uuid.uuid4(),
        "problem_number": "PRB-2024-000001",
        "title": "テスト問題",
        "description": None,
        "priority": "P3",
        "status": "New",
        "root_cause": None,
        "known_error": False,
        "workaround": None,
        "assigned_to": None,
        "reported_by": None,
        "resolved_at": None,
        "closed_at": None,
        "category": None,
        "affected_service": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    problem = MagicMock(spec=Problem)
    for k, v in defaults.items():
        setattr(problem, k, v)
    return problem


def _mock_db_returning(items):
    """DBモック: execute -> scalars().all() / scalar_one_or_none"""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = items
    result_mock.scalar_one_or_none.return_value = items[0] if items else None
    result_mock.scalar_one.return_value = len(items)
    db.execute.return_value = result_mock
    return db


def _mock_db_with_count_and_items(count, items):
    """DBモック: 最初のexecuteでcount、2番目でitems"""
    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = count

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = items

    db.execute.side_effect = [count_result, items_result]
    return db


# --- list_problems() テスト ---------------------------------------------------


async def test_list_problems_empty_direct():
    """list_problems() 直接呼び出し: 空リスト"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_problems(
        db=db,
        current_user=user,
        page=1,
        size=20,
        status_filter=None,
        priority=None,
        known_error=None,
    )

    assert result.total == 0
    assert result.items == []
    assert result.page == 1
    assert result.size == 20


async def test_list_problems_with_data_direct():
    """list_problems() 直接呼び出し: データあり"""
    user = _make_user()
    problem = _make_problem()
    db = _mock_db_with_count_and_items(1, [problem])

    result = await list_problems(
        db=db,
        current_user=user,
        page=1,
        size=20,
        status_filter=None,
        priority=None,
        known_error=None,
    )

    assert result.total == 1
    assert len(result.items) == 1


async def test_list_problems_with_status_filter_direct():
    """list_problems() 直接呼び出し: statusフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_problems(
        db=db,
        current_user=user,
        page=1,
        size=20,
        status_filter="New",
        priority=None,
        known_error=None,
    )

    assert result.total == 0


async def test_list_problems_with_priority_filter_direct():
    """list_problems() 直接呼び出し: priorityフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_problems(
        db=db,
        current_user=user,
        page=1,
        size=20,
        status_filter=None,
        priority="P1",
        known_error=None,
    )

    assert result.total == 0


async def test_list_problems_with_known_error_filter_direct():
    """list_problems() 直接呼び出し: known_errorフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_problems(
        db=db,
        current_user=user,
        page=1,
        size=20,
        status_filter=None,
        priority=None,
        known_error=False,
    )

    assert result.total == 0


async def test_list_problems_pagination_direct():
    """list_problems() 直接呼び出し: ページネーション"""
    user = _make_user()
    db = _mock_db_with_count_and_items(50, [])

    result = await list_problems(
        db=db,
        current_user=user,
        page=3,
        size=10,
        status_filter=None,
        priority=None,
        known_error=None,
    )

    assert result.total == 50
    assert result.page == 3
    assert result.size == 10
    assert result.pages == 5


# --- create_problem() テスト --------------------------------------------------


async def test_create_problem_direct():
    """create_problem() 直接呼び出し: 正常作成"""
    user = _make_user()
    problem = _make_problem()
    db = AsyncMock()

    data = ProblemCreate(title="テスト問題", priority="P3")

    with patch(
        "src.api.v1.problems.problem_service.create_problem",
        new=AsyncMock(return_value=problem),
    ):
        result = await create_problem(data=data, db=db, current_user=user)

    assert result.problem_number == "PRB-2024-000001"


# --- get_problem() テスト -----------------------------------------------------


async def test_get_problem_found_direct():
    """get_problem() 直接呼び出し: 問題が見つかる"""
    user = _make_user()
    problem = _make_problem()
    db = _mock_db_returning([problem])

    result = await get_problem(problem_id=problem.problem_id, db=db, current_user=user)

    assert result == problem


async def test_get_problem_not_found_direct():
    """get_problem() 直接呼び出し: 問題が見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    with pytest.raises(HTTPException) as exc_info:
        await get_problem(problem_id=uuid.uuid4(), db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- update_problem() テスト --------------------------------------------------


async def test_update_problem_success_direct():
    """update_problem() 直接呼び出し: 正常更新"""
    user = _make_user()
    problem = _make_problem()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = problem
    db.execute.return_value = result_mock

    data = ProblemUpdate(root_cause="ディスクI/Oボトルネック")
    result = await update_problem(
        problem_id=problem.problem_id, data=data, db=db, current_user=user
    )

    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once()


async def test_update_problem_not_found_direct():
    """update_problem() 直接呼び出し: 問題が見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    data = ProblemUpdate(root_cause="不明")
    with pytest.raises(HTTPException) as exc_info:
        await update_problem(problem_id=uuid.uuid4(), data=data, db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- transition_problem_status() テスト ---------------------------------------


async def test_transition_problem_success_direct():
    """transition_problem_status() 直接呼び出し: 正常遷移"""
    user = _make_user()
    problem = _make_problem(status="New")
    transitioned = _make_problem(status="Under_Investigation")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = problem
    db.execute.return_value = result_mock

    transition = ProblemStatusTransition(new_status="Under_Investigation")

    with patch(
        "src.api.v1.problems.problem_service.transition_problem_status",
        new=AsyncMock(return_value=transitioned),
    ):
        result = await transition_problem_status(
            problem_id=problem.problem_id,
            transition=transition,
            db=db,
            current_user=user,
        )

    assert result.status == "Under_Investigation"


async def test_transition_problem_not_found_direct():
    """transition_problem_status() 直接呼び出し: 問題が見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    transition = ProblemStatusTransition(new_status="Under_Investigation")

    with pytest.raises(HTTPException) as exc_info:
        await transition_problem_status(
            problem_id=uuid.uuid4(),
            transition=transition,
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 404


async def test_transition_problem_invalid_direct():
    """transition_problem_status() 直接呼び出し: 不正遷移 -> 422"""
    from fastapi import HTTPException

    user = _make_user()
    problem = _make_problem(status="New")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = problem
    db.execute.return_value = result_mock

    transition = ProblemStatusTransition(new_status="Resolved")

    with (
        patch(
            "src.api.v1.problems.problem_service.transition_problem_status",
            new=AsyncMock(side_effect=ValueError("無効な遷移")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await transition_problem_status(
            problem_id=problem.problem_id,
            transition=transition,
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 422


# --- set_known_error() テスト -------------------------------------------------


async def test_set_known_error_success_direct():
    """set_known_error() 直接呼び出し: 既知エラー登録成功"""
    user = _make_user()
    problem = _make_problem(status="Under_Investigation")
    known_error_problem = _make_problem(status="Known_Error", known_error=True)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = problem
    db.execute.return_value = result_mock

    data = KnownErrorUpdate(workaround="サービス再起動で一時回避")

    with patch(
        "src.api.v1.problems.problem_service.mark_as_known_error",
        new=AsyncMock(return_value=known_error_problem),
    ):
        result = await set_known_error(
            problem_id=problem.problem_id, data=data, db=db, current_user=user
        )

    assert result.status == "Known_Error"
    assert result.known_error is True


async def test_set_known_error_not_found_direct():
    """set_known_error() 直接呼び出し: 問題が見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    data = KnownErrorUpdate(workaround="テスト")

    with pytest.raises(HTTPException) as exc_info:
        await set_known_error(problem_id=uuid.uuid4(), data=data, db=db, current_user=user)

    assert exc_info.value.status_code == 404


async def test_set_known_error_invalid_direct():
    """set_known_error() 直接呼び出し: 不正状態 -> 422"""
    from fastapi import HTTPException

    user = _make_user()
    problem = _make_problem(status="Closed")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = problem
    db.execute.return_value = result_mock

    data = KnownErrorUpdate(workaround="テスト回避策")

    with (
        patch(
            "src.api.v1.problems.problem_service.mark_as_known_error",
            new=AsyncMock(side_effect=ValueError("不正な状態")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await set_known_error(problem_id=problem.problem_id, data=data, db=db, current_user=user)

    assert exc_info.value.status_code == 422


# --- analyze_problem_rca() テスト ---------------------------------------------


async def test_analyze_rca_success_direct():
    """analyze_problem_rca() 直接呼び出し: RCA分析成功"""
    from src.services.rca_service import RCAResult

    user = _make_user()
    db = AsyncMock()
    problem_id = uuid.uuid4()

    mock_result = RCAResult(
        problem_id=str(problem_id),
        candidates=[],
        similar_incidents=[],
        affected_cis=[],
        analysis_summary="テスト分析結果",
    )

    with patch(
        "src.api.v1.problems.rca_service.analyze_problem",
        new=AsyncMock(return_value=mock_result),
    ):
        result = await analyze_problem_rca(problem_id=problem_id, db=db, current_user=user)

    assert result.problem_id == str(problem_id)
    assert result.analysis_summary == "テスト分析結果"
