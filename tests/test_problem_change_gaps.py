"""problem_service.py / problems.py / change_service.py / rbac.py カバレッジ向上

対象:
  src/services/problem_service.py (78%) → lines 26-29, 42-44, 62-66
  src/api/v1/problems.py (78%) → lines 206-222, 243-252
  src/services/change_service.py (79%) → lines 50-53, 96-99, 117-118, 134-141
  src/middleware/rbac.py (83%) → lines 44, 49, 52-55
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_problem_mock(
    problem_id=None,
    status="New",
    priority="P1",
    problem_number="PRB-2026-000001",
    known_error=False,
):
    p = MagicMock()
    p.problem_id = problem_id or uuid.uuid4()
    p.problem_number = problem_number
    p.status = status
    p.priority = priority
    p.known_error = known_error
    p.resolved_at = None
    p.closed_at = None
    p.root_cause = None
    p.workaround = None
    return p


def _make_change_mock(
    change_id=None,
    status="Draft",
    change_number="CHG-2026-000001",
):
    c = MagicMock()
    c.change_id = change_id or uuid.uuid4()
    c.change_number = change_number
    c.status = status
    c.actual_start_at = None
    c.actual_end_at = None
    c.cab_approved_by = None
    c.cab_reviewed_at = None
    c.cab_notes = None
    return c


def _make_db_for_nextval(seq_value: int):
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = seq_value
    db.execute = AsyncMock(return_value=result_mock)
    return db


def _make_execute_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ─── problem_service._get_next_problem_number (lines 26-29) ─────────────────


async def test_get_next_problem_number_format():
    """_get_next_problem_number: PRB-YYYY-NNNNNN 形式で返す"""
    from src.services.problem_service import _get_next_problem_number

    db = _make_db_for_nextval(seq_value=7)
    result = await _get_next_problem_number(db)

    year = datetime.now(UTC).year
    assert result == f"PRB-{year}-000007"


async def test_get_next_problem_number_padding():
    """_get_next_problem_number: 6桁ゼロ埋め"""
    from src.services.problem_service import _get_next_problem_number

    db = _make_db_for_nextval(seq_value=1)
    result = await _get_next_problem_number(db)
    assert result.endswith("-000001")


# ─── problem_service.create_problem (lines 42-44) ────────────────────────────


async def test_create_problem_returns_problem():
    """create_problem: Problem オブジェクトを返す（lines 42-44）"""
    from src.services.problem_service import create_problem

    db = _make_db_for_nextval(seq_value=3)
    db.add = MagicMock()

    problem_instance = _make_problem_mock()
    problem_instance.problem_number = "PRB-2026-000003"

    with patch("src.services.problem_service.Problem", return_value=problem_instance):
        result = await create_problem(db, {"title": "テスト問題", "priority": "P2"})

    db.add.assert_called_once_with(problem_instance)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(problem_instance)
    assert result is problem_instance


# ─── problem_service.transition_problem_status (lines 62-66) ─────────────────


async def test_transition_problem_resolved_sets_resolved_at():
    """transition_problem_status: Resolved → resolved_at 設定（lines 57-66）"""
    from src.services.problem_service import transition_problem_status

    db = AsyncMock()
    problem = _make_problem_mock(status="Under_Investigation")

    result = await transition_problem_status(db, problem, "Resolved")

    assert problem.status == "Resolved"
    assert problem.resolved_at is not None
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(problem)


async def test_transition_problem_closed_sets_closed_at():
    """transition_problem_status: Closed → closed_at 設定"""
    from src.services.problem_service import transition_problem_status

    db = AsyncMock()
    problem = _make_problem_mock(status="Resolved")

    await transition_problem_status(db, problem, "Closed")

    assert problem.status == "Closed"
    assert problem.closed_at is not None


async def test_transition_problem_invalid_raises():
    """transition_problem_status: 無効遷移 → ValueError"""
    from src.services.problem_service import transition_problem_status

    db = AsyncMock()
    problem = _make_problem_mock(status="Closed")

    with pytest.raises(ValueError, match="遷移は許可されていません"):
        await transition_problem_status(db, problem, "New")


# ─── problems.py API save_rca (lines 206-222) ─────────────────────────────────


async def test_save_rca_success_with_factors_and_fix():
    """save_rca: contributing_factors + permanent_fix でRCA保存（lines 213-222）"""
    from src.api.v1.problems import save_rca

    problem = _make_problem_mock(status="Under_Investigation")
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(problem))

    class RCAReq:
        root_cause = "原因はメモリリーク"
        contributing_factors = ["高負荷", "不適切なGC設定"]
        permanent_fix = "GCチューニングとメモリ増設"

    current_user = MagicMock()
    result = await save_rca(
        problem_id=problem.problem_id,
        data=RCAReq(),
        db=db,
        current_user=current_user,
    )

    assert "原因はメモリリーク" in problem.root_cause
    assert "高負荷" in problem.root_cause
    assert "GCチューニング" in problem.root_cause
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(problem)


async def test_save_rca_without_factors():
    """save_rca: contributing_factors なし → root_cause のみ保存"""
    from src.api.v1.problems import save_rca

    problem = _make_problem_mock()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(problem))

    class RCAReq:
        root_cause = "シンプルな原因"
        contributing_factors = []
        permanent_fix = None

    current_user = MagicMock()
    await save_rca(
        problem_id=problem.problem_id,
        data=RCAReq(),
        db=db,
        current_user=current_user,
    )

    assert problem.root_cause == "シンプルな原因"


async def test_save_rca_not_found_raises_404():
    """save_rca: 問題不存在 → 404"""
    from src.api.v1.problems import save_rca

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(None))

    class RCAReq:
        root_cause = "テスト"
        contributing_factors = []
        permanent_fix = None

    with pytest.raises(HTTPException) as exc_info:
        await save_rca(
            problem_id=uuid.uuid4(),
            data=RCAReq(),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


# ─── problems.py API mark_known_error (lines 243-252) ────────────────────────


async def test_mark_known_error_success():
    """mark_known_error: 正常登録（lines 243-252）"""
    from src.api.v1.problems import mark_known_error
    from src.schemas.problem import KnownErrorUpdate

    problem = _make_problem_mock(status="Under_Investigation")
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(problem))

    data = KnownErrorUpdate(workaround="サービス再起動で回避可能")

    with patch(
        "src.services.problem_service.mark_as_known_error",
        new=AsyncMock(return_value=problem),
    ):
        result = await mark_known_error(
            problem_id=problem.problem_id,
            data=data,
            db=db,
            current_user=MagicMock(),
        )

    assert result is problem


async def test_mark_known_error_not_found_raises_404():
    """mark_known_error: 問題不存在 → 404"""
    from src.api.v1.problems import mark_known_error
    from src.schemas.problem import KnownErrorUpdate

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(None))

    with pytest.raises(HTTPException) as exc_info:
        await mark_known_error(
            problem_id=uuid.uuid4(),
            data=KnownErrorUpdate(workaround="回避策"),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_mark_known_error_value_error_raises_422():
    """mark_known_error: ValueError → 422（lines 250-251）"""
    from src.api.v1.problems import mark_known_error
    from src.schemas.problem import KnownErrorUpdate

    problem = _make_problem_mock()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(problem))

    with patch(
        "src.services.problem_service.mark_as_known_error",
        new=AsyncMock(side_effect=ValueError("ワークアラウンドが必須")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await mark_known_error(
                problem_id=problem.problem_id,
                data=KnownErrorUpdate(workaround="x"),
                db=db,
                current_user=MagicMock(),
            )

    assert exc_info.value.status_code == 422


# ─── change_service._get_next_change_number (lines 50-53) ────────────────────


async def test_get_next_change_number_format():
    """_get_next_change_number: CHG-YYYY-NNNNNN 形式"""
    from src.services.change_service import _get_next_change_number

    db = _make_db_for_nextval(seq_value=5)
    result = await _get_next_change_number(db)

    year = datetime.now(UTC).year
    assert result == f"CHG-{year}-000005"


# ─── change_service.create_change (lines 96-99) ──────────────────────────────


async def test_create_change_increments_metrics():
    """create_change: metrics.changes_created_total インクリメント（lines 96-99）"""
    from src.core.metrics import metrics
    from src.services.change_service import create_change

    db = _make_db_for_nextval(seq_value=1)
    db.add = MagicMock()

    change_instance = _make_change_mock()
    change_instance.change_number = "CHG-2026-000001"

    before = metrics.changes_created_total

    with patch("src.services.change_service.Change", return_value=change_instance):
        result = await create_change(
            db,
            {"title": "テスト変更", "change_type": "Normal"},
        )

    assert metrics.changes_created_total == before + 1
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(change_instance)


# ─── change_service.transition_change_status (lines 117-118) ─────────────────


async def test_transition_change_in_progress_sets_actual_start():
    """transition_change_status: In_Progress → actual_start_at 設定（lines 111-112）"""
    from src.services.change_service import transition_change_status

    db = AsyncMock()
    change = _make_change_mock(status="Scheduled")

    await transition_change_status(db, change, "In_Progress")

    assert change.status == "In_Progress"
    assert change.actual_start_at is not None
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(change)


async def test_transition_change_completed_sets_actual_end():
    """transition_change_status: Completed → actual_end_at 設定（line 113-114）"""
    from src.services.change_service import transition_change_status

    db = AsyncMock()
    change = _make_change_mock(status="In_Progress")

    await transition_change_status(db, change, "Completed")

    assert change.status == "Completed"
    assert change.actual_end_at is not None


async def test_transition_change_invalid_raises():
    """transition_change_status: 無効遷移 → ValueError"""
    from src.services.change_service import transition_change_status

    db = AsyncMock()
    change = _make_change_mock(status="Draft")

    with pytest.raises(ValueError, match="遷移は許可されていません"):
        await transition_change_status(db, change, "Completed")


# ─── change_service.approve_by_cab (lines 134-141) ───────────────────────────


async def test_approve_by_cab_approved():
    """approve_by_cab: approved=True → status=Approved + logger（lines 134-141）"""
    from src.services.change_service import approve_by_cab

    db = AsyncMock()
    change = _make_change_mock(status="CAB_Review")
    approver_id = uuid.uuid4()

    result = await approve_by_cab(db, change, approver_id, approved=True, notes="問題なし")

    assert change.status == "Approved"
    assert change.cab_approved_by == approver_id
    assert change.cab_notes == "問題なし"
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(change)


async def test_approve_by_cab_rejected():
    """approve_by_cab: approved=False → status=Rejected"""
    from src.services.change_service import approve_by_cab

    db = AsyncMock()
    change = _make_change_mock(status="CAB_Review")
    approver_id = uuid.uuid4()

    await approve_by_cab(db, change, approver_id, approved=False, notes="リスク大")

    assert change.status == "Rejected"
    assert change.cab_approved_by is None


async def test_approve_by_cab_not_in_review_raises():
    """approve_by_cab: CAB_Review 以外 → ValueError（line 125-126）"""
    from src.services.change_service import approve_by_cab

    db = AsyncMock()
    change = _make_change_mock(status="Draft")

    with pytest.raises(ValueError, match="CABレビュー状態のみ"):
        await approve_by_cab(db, change, uuid.uuid4(), approved=True, notes=None)


# ─── rbac.py get_current_user (lines 44, 49, 52-55) ─────────────────────────


async def test_get_current_user_user_id_none_raises_401():
    """get_current_user: sub=None → 401（line 44）"""
    from src.middleware.rbac import get_current_user

    db = AsyncMock()
    with patch("src.middleware.rbac.decode_token", return_value={"sub": None}):
        with patch("src.middleware.rbac.is_token_blacklisted", new=AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="fake-token", db=db)

    assert exc_info.value.status_code == 401


async def test_get_current_user_blacklisted_raises_401():
    """get_current_user: ブラックリストトークン → 401（line 49）"""
    from src.middleware.rbac import get_current_user

    db = AsyncMock()
    with patch(
        "src.middleware.rbac.decode_token",
        return_value={"sub": str(uuid.uuid4())},
    ):
        with patch("src.middleware.rbac.is_token_blacklisted", new=AsyncMock(return_value=True)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="blacklisted-token", db=db)

    assert exc_info.value.status_code == 401


async def test_get_current_user_not_found_raises_401():
    """get_current_user: ユーザー不存在 → 401（lines 52-54）"""
    from src.middleware.rbac import get_current_user

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "src.middleware.rbac.decode_token",
        return_value={"sub": str(uuid.uuid4())},
    ):
        with patch("src.middleware.rbac.is_token_blacklisted", new=AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="valid-token", db=db)

    assert exc_info.value.status_code == 401


async def test_get_current_user_inactive_raises_401():
    """get_current_user: is_active=False → 401（line 53-54）"""
    from src.middleware.rbac import get_current_user

    db = AsyncMock()
    inactive_user = MagicMock()
    inactive_user.is_active = False

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inactive_user
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "src.middleware.rbac.decode_token",
        return_value={"sub": str(uuid.uuid4())},
    ):
        with patch("src.middleware.rbac.is_token_blacklisted", new=AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="valid-token", db=db)

    assert exc_info.value.status_code == 401
