"""incidents.py エンドポイント関数の直接呼び出しユニットテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.incidents import (
    bulk_assign_incidents,
    bulk_update_incidents,
    create_comment,
    create_incident,
    delete_comment,
    get_incident,
    link_problem,
    list_comments,
    list_incidents,
    run_ai_triage,
    suggest_problem,
    transition_incident_status,
    update_incident,
)
from src.models.incident import Incident
from src.models.incident_comment import IncidentComment
from src.models.problem import Problem
from src.models.user import User, UserRole
from src.schemas.incident import (
    BulkIncidentUpdate,
    IncidentBulkAssign,
    IncidentCommentCreate,
    IncidentCreate,
    IncidentStatusTransition,
    IncidentUpdate,
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


def _make_incident(**overrides):
    defaults = {
        "incident_id": uuid.uuid4(),
        "incident_number": "INC-2024-000001",
        "title": "テストインシデント",
        "description": None,
        "priority": "P3",
        "status": "New",
        "assigned_to": None,
        "assigned_team_id": None,
        "reported_by": None,
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "sla_response_due_at": None,
        "sla_resolution_due_at": None,
        "sla_breached": False,
        "category": None,
        "subcategory": None,
        "affected_service": None,
        "resolution_notes": None,
        "ai_triage_notes": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    incident = MagicMock(spec=Incident)
    for k, v in defaults.items():
        setattr(incident, k, v)
    return incident


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


# --- list_incidents() テスト --------------------------------------------------


async def test_list_incidents_empty_direct():
    """list_incidents() 直接呼び出し: 空リスト"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter=None, priority=None
    )

    assert result.total == 0
    assert result.items == []
    assert result.page == 1
    assert result.size == 20


async def test_list_incidents_with_data_direct():
    """list_incidents() 直接呼び出し: データあり"""
    user = _make_user()
    incident = _make_incident()
    db = _mock_db_with_count_and_items(1, [incident])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter=None, priority=None
    )

    assert result.total == 1
    assert len(result.items) == 1


async def test_list_incidents_with_status_filter_direct():
    """list_incidents() 直接呼び出し: statusフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter="New", priority=None
    )

    assert result.total == 0


async def test_list_incidents_with_priority_filter_direct():
    """list_incidents() 直接呼び出し: priorityフィルタ"""
    user = _make_user()
    db = _mock_db_with_count_and_items(0, [])

    result = await list_incidents(
        db=db, current_user=user, page=1, size=20, status_filter=None, priority="P1"
    )

    assert result.total == 0


async def test_list_incidents_pagination_direct():
    """list_incidents() 直接呼び出し: ページネーション"""
    user = _make_user()
    db = _mock_db_with_count_and_items(50, [])

    result = await list_incidents(
        db=db, current_user=user, page=3, size=10, status_filter=None, priority=None
    )

    assert result.total == 50
    assert result.page == 3
    assert result.size == 10
    assert result.pages == 5


# --- create_incident() テスト -------------------------------------------------


async def test_create_incident_direct():
    """create_incident() 直接呼び出し: 正常作成"""
    user = _make_user()
    incident = _make_incident()
    db = AsyncMock()
    background_tasks = MagicMock()

    data = IncidentCreate(title="テストインシデント", priority="P3")

    with patch(
        "src.api.v1.incidents.incident_service.create_incident",
        new=AsyncMock(return_value=incident),
    ):
        result = await create_incident(
            data=data, background_tasks=background_tasks, db=db, current_user=user
        )

    assert result.incident_number == "INC-2024-000001"
    background_tasks.add_task.assert_called_once()


# --- get_incident() テスト ----------------------------------------------------


async def test_get_incident_found_direct():
    """get_incident() 直接呼び出し: インシデントが見つかる"""
    user = _make_user()
    incident = _make_incident()
    db = _mock_db_returning([incident])

    result = await get_incident(incident_id=incident.incident_id, db=db, current_user=user)

    assert result == incident


async def test_get_incident_not_found_direct():
    """get_incident() 直接呼び出し: インシデントが見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    with pytest.raises(HTTPException) as exc_info:
        await get_incident(incident_id=uuid.uuid4(), db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- update_incident() テスト -------------------------------------------------


async def test_update_incident_success_direct():
    """update_incident() 直接呼び出し: 正常更新"""
    user = _make_user()
    incident = _make_incident()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    data = IncidentUpdate(description="更新された説明")
    result = await update_incident(
        incident_id=incident.incident_id, data=data, db=db, current_user=user
    )

    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once()


async def test_update_incident_not_found_direct():
    """update_incident() 直接呼び出し: インシデントが見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    data = IncidentUpdate(description="更新")
    with pytest.raises(HTTPException) as exc_info:
        await update_incident(incident_id=uuid.uuid4(), data=data, db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- transition_incident_status() テスト --------------------------------------


async def test_transition_incident_success_direct():
    """transition_incident_status() 直接呼び出し: 正常遷移"""
    user = _make_user()
    incident = _make_incident(status="New")
    transitioned = _make_incident(status="Acknowledged")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    transition = IncidentStatusTransition(new_status="Acknowledged")

    with patch(
        "src.api.v1.incidents.incident_service.transition_status",
        new=AsyncMock(return_value=transitioned),
    ):
        result = await transition_incident_status(
            incident_id=incident.incident_id,
            transition=transition,
            db=db,
            current_user=user,
        )

    assert result.status == "Acknowledged"


async def test_transition_incident_not_found_direct():
    """transition_incident_status() 直接呼び出し: インシデントが見つからない -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    transition = IncidentStatusTransition(new_status="Acknowledged")

    with pytest.raises(HTTPException) as exc_info:
        await transition_incident_status(
            incident_id=uuid.uuid4(),
            transition=transition,
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 404


async def test_transition_incident_invalid_direct():
    """transition_incident_status() 直接呼び出し: 不正遷移 -> 422"""
    from fastapi import HTTPException

    user = _make_user()
    incident = _make_incident(status="New")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    transition = IncidentStatusTransition(new_status="Closed")

    with (
        patch(
            "src.api.v1.incidents.incident_service.transition_status",
            new=AsyncMock(side_effect=ValueError("無効な遷移")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await transition_incident_status(
            incident_id=incident.incident_id,
            transition=transition,
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 422


# --- run_ai_triage() テスト ---------------------------------------------------


def _make_triage_result(**overrides):
    defaults = {
        "priority": "P2",
        "category": "network",
        "confidence": 0.85,
        "reasoning": "ネットワーク関連のキーワードが多い",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


async def test_run_ai_triage_success_direct():
    """run_ai_triage() 直接呼び出し: 正常にトリアージ実行"""
    user = _make_user()
    incident = _make_incident(ai_triage_notes="AI解析完了")
    db = _mock_db_returning([incident])
    triage = _make_triage_result()

    with patch(
        "src.api.v1.incidents.ai_triage_service.apply_triage_to_incident",
        new=AsyncMock(return_value=triage),
    ):
        result = await run_ai_triage(
            incident_id=incident.incident_id, db=db, current_user=user
        )

    assert result["priority"] == "P2"
    assert result["category"] == "network"
    assert result["confidence"] == 0.85
    assert "incident_id" in result
    db.flush.assert_awaited()


async def test_run_ai_triage_not_found_direct():
    """run_ai_triage() 直接呼び出し: インシデントなし -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_returning([])

    with pytest.raises(HTTPException) as exc_info:
        await run_ai_triage(incident_id=uuid.uuid4(), db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- bulk_update_incidents() テスト -------------------------------------------


async def test_bulk_update_close_direct():
    """bulk_update_incidents() 直接呼び出し: close アクション"""
    user = _make_user()
    iid1 = uuid.uuid4()
    iid2 = uuid.uuid4()
    incident1 = _make_incident(incident_id=iid1, status="New")
    incident2 = _make_incident(incident_id=iid2, status="New")

    db = AsyncMock()
    result1 = MagicMock()
    result1.scalar_one_or_none.return_value = incident1
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = incident2
    db.execute.side_effect = [result1, result2]

    body = BulkIncidentUpdate(incident_ids=[iid1, iid2], action="close")
    result = await bulk_update_incidents(body=body, db=db, current_user=user)

    assert result.updated_count == 2
    assert len(result.failed_ids) == 0
    assert incident1.status == "Closed"
    assert incident2.status == "Closed"


async def test_bulk_update_assign_direct():
    """bulk_update_incidents() 直接呼び出し: assign アクション"""
    user = _make_user()
    iid = uuid.uuid4()
    assignee_id = uuid.uuid4()
    incident = _make_incident(incident_id=iid)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    body = BulkIncidentUpdate(incident_ids=[iid], action="assign", assignee_id=assignee_id)
    result = await bulk_update_incidents(body=body, db=db, current_user=user)

    assert result.updated_count == 1
    assert incident.assigned_to == assignee_id


async def test_bulk_update_set_priority_direct():
    """bulk_update_incidents() 直接呼び出し: set_priority アクション"""
    user = _make_user()
    iid = uuid.uuid4()
    incident = _make_incident(incident_id=iid, priority="P3")

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    body = BulkIncidentUpdate(incident_ids=[iid], action="set_priority", priority="P1")
    result = await bulk_update_incidents(body=body, db=db, current_user=user)

    assert result.updated_count == 1
    assert incident.priority == "P1"


async def test_bulk_update_not_found_direct():
    """bulk_update_incidents() 直接呼び出し: インシデントなし -> failed_ids に追加"""
    user = _make_user()
    iid = uuid.uuid4()

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    body = BulkIncidentUpdate(incident_ids=[iid], action="close")
    result = await bulk_update_incidents(body=body, db=db, current_user=user)

    assert result.updated_count == 0
    assert iid in result.failed_ids


async def test_bulk_update_invalid_action_direct():
    """bulk_update_incidents() 直接呼び出し: 不明なアクション -> failed_ids"""
    user = _make_user()
    iid = uuid.uuid4()
    incident = _make_incident(incident_id=iid)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident
    db.execute.return_value = result_mock

    body = BulkIncidentUpdate(incident_ids=[iid], action="unknown_action")
    result = await bulk_update_incidents(body=body, db=db, current_user=user)

    assert result.updated_count == 0
    assert iid in result.failed_ids


# --- bulk_assign_incidents() テスト -------------------------------------------


async def test_bulk_assign_success_direct():
    """bulk_assign_incidents() 直接呼び出し: 担当者割り当て成功"""
    user = _make_user()
    iid1 = uuid.uuid4()
    iid2 = uuid.uuid4()
    assignee_id = uuid.uuid4()
    team_id = uuid.uuid4()
    incident1 = _make_incident(incident_id=iid1)
    incident2 = _make_incident(incident_id=iid2)

    db = AsyncMock()
    result1 = MagicMock()
    result1.scalar_one_or_none.return_value = incident1
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = incident2
    db.execute.side_effect = [result1, result2]

    data = IncidentBulkAssign(
        incident_ids=[iid1, iid2], assigned_to=assignee_id, assigned_team_id=team_id
    )
    result = await bulk_assign_incidents(data=data, db=db, current_user=user)

    assert result["updated"] == 2
    assert len(result["incident_ids"]) == 2
    assert incident1.assigned_to == assignee_id
    assert incident1.assigned_team_id == team_id


async def test_bulk_assign_not_found_direct():
    """bulk_assign_incidents() 直接呼び出し: インシデントなし -> スキップ"""
    user = _make_user()
    iid = uuid.uuid4()

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    data = IncidentBulkAssign(incident_ids=[iid], assigned_to=uuid.uuid4())
    result = await bulk_assign_incidents(data=data, db=db, current_user=user)

    assert result["updated"] == 0


# --- list_comments() テスト ---------------------------------------------------


def _make_comment(**overrides):
    author = MagicMock()
    author.username = overrides.pop("author_username", "commentuser")
    defaults = {
        "comment_id": uuid.uuid4(),
        "incident_id": uuid.uuid4(),
        "author_id": uuid.uuid4(),
        "body": "テストコメント",
        "attachment_url": None,
        "created_at": NOW,
        "author": author,
    }
    defaults.update(overrides)
    comment = MagicMock(spec=IncidentComment)
    for k, v in defaults.items():
        setattr(comment, k, v)
    return comment


async def test_list_comments_empty_direct():
    """list_comments() 直接呼び出し: コメントなし"""
    user = _make_user()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute.return_value = result_mock

    result = await list_comments(incident_id=uuid.uuid4(), db=db, current_user=user)

    assert result == []


async def test_list_comments_with_data_direct():
    """list_comments() 直接呼び出し: コメントあり"""
    user = _make_user()
    incident_id = uuid.uuid4()
    comment = _make_comment(incident_id=incident_id)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [comment]
    db.execute.return_value = result_mock

    result = await list_comments(incident_id=incident_id, db=db, current_user=user)

    assert len(result) == 1
    assert result[0].body == "テストコメント"
    assert result[0].author_username == "commentuser"


# --- create_comment() テスト --------------------------------------------------


async def test_create_comment_success_direct():
    """create_comment() 直接呼び出し: コメント投稿成功"""
    user = _make_user()
    incident_id = uuid.uuid4()
    incident = _make_incident(incident_id=incident_id)

    db = AsyncMock()
    # 1回目のexecute: インシデント検索
    inc_result = MagicMock()
    inc_result.scalar_one_or_none.return_value = incident
    db.execute.return_value = inc_result

    # refresh後のcommentオブジェクトの設定
    comment_id = uuid.uuid4()

    async def mock_refresh(obj):
        obj.comment_id = comment_id
        obj.created_at = NOW

    db.refresh.side_effect = mock_refresh

    data = IncidentCommentCreate(body="新しいコメント")
    result = await create_comment(
        incident_id=incident_id, data=data, db=db, current_user=user
    )

    db.add.assert_called_once()
    db.flush.assert_awaited()
    assert result.body == "新しいコメント"
    assert result.author_username == "testadmin"


async def test_create_comment_not_found_direct():
    """create_comment() 直接呼び出し: インシデントなし -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    data = IncidentCommentCreate(body="コメント")
    with pytest.raises(HTTPException) as exc_info:
        await create_comment(incident_id=uuid.uuid4(), data=data, db=db, current_user=user)

    assert exc_info.value.status_code == 404


# --- delete_comment() テスト --------------------------------------------------


async def test_delete_comment_success_direct():
    """delete_comment() 直接呼び出し: 自分のコメントを削除"""
    user = _make_user()
    comment = _make_comment()
    comment.author_id = user.user_id  # 自分のコメント

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = comment
    db.execute.return_value = result_mock

    await delete_comment(
        incident_id=comment.incident_id,
        comment_id=comment.comment_id,
        db=db,
        current_user=user,
    )

    db.delete.assert_awaited_once_with(comment)
    db.flush.assert_awaited()


async def test_delete_comment_not_found_direct():
    """delete_comment() 直接呼び出し: コメントなし -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await delete_comment(
            incident_id=uuid.uuid4(),
            comment_id=uuid.uuid4(),
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 404


async def test_delete_comment_forbidden_direct():
    """delete_comment() 直接呼び出し: 他人のコメント削除 -> 403"""
    from fastapi import HTTPException

    user = _make_user(role=UserRole.OPERATOR)
    comment = _make_comment()
    comment.author_id = uuid.uuid4()  # 別ユーザーのコメント

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = comment
    db.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await delete_comment(
            incident_id=comment.incident_id,
            comment_id=comment.comment_id,
            db=db,
            current_user=user,
        )

    assert exc_info.value.status_code == 403


async def test_delete_comment_admin_can_delete_others_direct():
    """delete_comment() 直接呼び出し: SYSTEM_ADMINは他人のコメント削除可"""
    user = _make_user(role=UserRole.SYSTEM_ADMIN)
    comment = _make_comment()
    comment.author_id = uuid.uuid4()  # 別ユーザーのコメント

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = comment
    db.execute.return_value = result_mock

    # 例外が発生しないことを確認
    await delete_comment(
        incident_id=comment.incident_id,
        comment_id=comment.comment_id,
        db=db,
        current_user=user,
    )

    db.delete.assert_awaited_once_with(comment)


# --- link_problem() テスト ----------------------------------------------------


def _make_problem(**overrides):
    defaults = {
        "problem_id": uuid.uuid4(),
        "problem_number": "PRB-2024-000001",
        "title": "テスト問題",
        "description": "問題の詳細",
        "status": "New",
        "priority": "P3",
    }
    defaults.update(overrides)
    problem = MagicMock(spec=Problem)
    for k, v in defaults.items():
        setattr(problem, k, v)
    return problem


async def test_link_problem_success_direct():
    """link_problem() 直接呼び出し: 問題リンク成功"""
    from src.api.v1.incidents import LinkProblemRequest

    user = _make_user()
    incident = _make_incident()
    problem = _make_problem()

    db = AsyncMock()
    inc_result = MagicMock()
    inc_result.scalar_one_or_none.return_value = incident
    prob_result = MagicMock()
    prob_result.scalar_one_or_none.return_value = problem
    db.execute.side_effect = [inc_result, prob_result]

    body = LinkProblemRequest(problem_id=problem.problem_id)
    result = await link_problem(
        incident_id=incident.incident_id, body=body, db=db, current_user=user
    )

    assert result["linked"] is True
    assert result["problem_id"] == str(problem.problem_id)
    assert incident.linked_problem_id == body.problem_id
    db.flush.assert_awaited()


async def test_link_problem_incident_not_found_direct():
    """link_problem() 直接呼び出し: インシデントなし -> 404"""
    from fastapi import HTTPException

    from src.api.v1.incidents import LinkProblemRequest

    user = _make_user()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    body = LinkProblemRequest(problem_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        await link_problem(incident_id=uuid.uuid4(), body=body, db=db, current_user=user)

    assert exc_info.value.status_code == 404


async def test_link_problem_problem_not_found_direct():
    """link_problem() 直接呼び出し: 問題なし -> 404"""
    from fastapi import HTTPException

    from src.api.v1.incidents import LinkProblemRequest

    user = _make_user()
    incident = _make_incident()

    db = AsyncMock()
    inc_result = MagicMock()
    inc_result.scalar_one_or_none.return_value = incident
    prob_result = MagicMock()
    prob_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [inc_result, prob_result]

    body = LinkProblemRequest(problem_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        await link_problem(
            incident_id=incident.incident_id, body=body, db=db, current_user=user
        )

    assert exc_info.value.status_code == 404


# --- suggest_problem() テスト -------------------------------------------------


async def test_suggest_problem_no_problems_direct():
    """suggest_problem() 直接呼び出し: 関連問題なし"""
    user = _make_user()
    incident = _make_incident(affected_service="network")

    db = AsyncMock()
    inc_result = MagicMock()
    inc_result.scalar_one_or_none.return_value = incident
    prob_result = MagicMock()
    prob_result.scalars.return_value.all.return_value = []
    db.execute.side_effect = [inc_result, prob_result]

    result = await suggest_problem(
        incident_id=incident.incident_id, db=db, current_user=user
    )

    assert result["suggestions"] == []


async def test_suggest_problem_with_match_direct():
    """suggest_problem() 直接呼び出し: サービス名一致で提案あり"""
    user = _make_user()
    incident = _make_incident(affected_service="network", priority="P2")
    problem = _make_problem(title="network障害調査", priority="P2")

    db = AsyncMock()
    inc_result = MagicMock()
    inc_result.scalar_one_or_none.return_value = incident
    prob_result = MagicMock()
    prob_result.scalars.return_value.all.return_value = [problem]
    db.execute.side_effect = [inc_result, prob_result]

    result = await suggest_problem(
        incident_id=incident.incident_id, db=db, current_user=user
    )

    assert len(result["suggestions"]) >= 1
    assert result["suggestions"][0]["problem_id"] == str(problem.problem_id)
    # タイトル一致(0.5) + 優先度一致(0.2) = 0.7
    assert result["suggestions"][0]["similarity_score"] >= 0.5


async def test_suggest_problem_incident_not_found_direct():
    """suggest_problem() 直接呼び出し: インシデントなし -> 404"""
    from fastapi import HTTPException

    user = _make_user()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await suggest_problem(incident_id=uuid.uuid4(), db=db, current_user=user)

    assert exc_info.value.status_code == 404


async def test_suggest_problem_max_5_direct():
    """suggest_problem() 直接呼び出し: 提案は最大5件"""
    user = _make_user()
    incident = _make_incident(affected_service="network", priority="P1")
    # 6件の問題を作成（全てnetworkを含む）
    problems = [_make_problem(title=f"network障害{i}", priority="P1") for i in range(6)]

    db = AsyncMock()
    inc_result = MagicMock()
    inc_result.scalar_one_or_none.return_value = incident
    prob_result = MagicMock()
    prob_result.scalars.return_value.all.return_value = problems
    db.execute.side_effect = [inc_result, prob_result]

    result = await suggest_problem(
        incident_id=incident.incident_id, db=db, current_user=user
    )

    assert len(result["suggestions"]) <= 5
