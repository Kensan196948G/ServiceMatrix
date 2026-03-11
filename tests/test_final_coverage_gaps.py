"""最終カバレッジギャップ テスト (99% → 99.8%)

対象:
  auto_repair_service.py line 260: "performance" 症状 → 仮説生成
  notification_webhook_service.py line 56: unknown webhook_type → False返却
  change_impact_service.py line 110: キーワードなし → 空リスト返却
  incidents.py lines 286-287: bulk_update 成功パス (flush / updated++)
  incidents.py line 508: find_related_problems similarity > 0
  auth.py line 115: list_users エンドポイント
  ai.py line 275: ai_status エンドポイント
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── auto_repair_service.py line 260: "performance" 症状 ─────────────────────


def test_hypothesize_root_cause_performance():
    """_hypothesize_root_cause: 'performance' 症状 → パフォーマンス劣化仮説（line 260）"""
    from src.services.auto_repair_service import AutoRepairService

    svc = AutoRepairService()
    result = svc._hypothesize_root_cause(["performance"], "api response is slow")

    assert "パフォーマンス" in result


def test_hypothesize_root_cause_all_symptoms():
    """_hypothesize_root_cause: 全症状 → 複数仮説を / で結合"""
    from src.services.auto_repair_service import AutoRepairService

    svc = AutoRepairService()
    result = svc._hypothesize_root_cause(
        ["outage", "error", "timeout", "performance"],
        "full system meltdown",
    )

    assert "サービス全体" in result
    assert "アプリケーションエラー" in result
    assert "応答タイムアウト" in result
    assert "パフォーマンス" in result
    assert "/" in result


# ─── notification_webhook_service.py line 56: unknown type → False ───────────


async def test_send_webhook_notification_unknown_type_returns_false():
    """send_webhook_notification: webhook_type='pagerduty' → False 返却（line 56）"""
    from src.services.notification_webhook_service import send_webhook_notification

    result = await send_webhook_notification(
        "https://webhook.example.com", "pagerduty", "test message"
    )

    assert result is False


async def test_send_webhook_notification_empty_type_returns_false():
    """send_webhook_notification: webhook_type='' → False 返却"""
    from src.services.notification_webhook_service import send_webhook_notification

    result = await send_webhook_notification("https://webhook.example.com", "", "msg")

    assert result is False


# ─── change_impact_service.py line 110: no keywords → empty list ─────────────


async def test_find_affected_cis_short_words_returns_empty():
    """_find_affected_cis: 3文字以上の単語なし → 空リスト（line 110）"""
    from src.services.change_impact_service import ChangeImpactService

    svc = ChangeImpactService()
    db = AsyncMock()

    # タイトルが短い単語のみ → keywords が空 → return []
    result = await svc._find_affected_cis(db, "a b c")

    assert result == []
    db.execute.assert_not_called()


async def test_find_affected_cis_empty_title_returns_empty():
    """_find_affected_cis: 空タイトル → 空リスト"""
    from src.services.change_impact_service import ChangeImpactService

    svc = ChangeImpactService()
    db = AsyncMock()

    result = await svc._find_affected_cis(db, "")

    assert result == []
    db.execute.assert_not_called()


# ─── incidents.py lines 286-287: bulk_update 成功パス ────────────────────────


async def test_bulk_update_incidents_close_action():
    """bulk_update_incidents: action=close → flush/updated++（lines 286-287）"""
    from src.api.v1.incidents import bulk_update_incidents
    from src.schemas.incident import BulkIncidentUpdate

    iid = uuid.uuid4()
    inc_mock = MagicMock()
    inc_mock.status = "New"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inc_mock
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    update_data = BulkIncidentUpdate(
        incident_ids=[iid],
        action="close",
    )

    result = await bulk_update_incidents(
        body=update_data,
        db=db,
        current_user=MagicMock(),
    )

    assert result.updated_count == 1
    db.flush.assert_called()


async def test_bulk_update_incidents_not_found_goes_to_failed():
    """bulk_update_incidents: 存在しないインシデント → failed_ids に追加"""
    from src.api.v1.incidents import bulk_update_incidents
    from src.schemas.incident import BulkIncidentUpdate

    iid = uuid.uuid4()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    update_data = BulkIncidentUpdate(
        incident_ids=[iid],
        action="close",
    )

    result = await bulk_update_incidents(
        body=update_data,
        db=db,
        current_user=MagicMock(),
    )

    assert result.updated_count == 0
    assert len(result.failed_ids) == 1


# ─── incidents.py line 508: suggest_problem similarity > 0 ──────────────────


async def test_suggest_problem_with_matching_service():
    """suggest_problem: affected_service が problem.title に含まれる → score > 0（line 508）"""
    from src.api.v1.incidents import suggest_problem

    problem_mock = MagicMock()
    problem_mock.problem_id = uuid.uuid4()
    problem_mock.title = "database connection pool exhausted"
    problem_mock.description = "postgresql connections failed"
    problem_mock.priority = "P2"

    incident_mock = MagicMock()
    incident_mock.incident_id = uuid.uuid4()
    incident_mock.affected_service = "database"
    incident_mock.priority = "P2"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident_mock
    problem_result = MagicMock()
    problem_result.scalars.return_value.all.return_value = [problem_mock]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[result_mock, problem_result])

    result = await suggest_problem(
        incident_id=incident_mock.incident_id,
        db=db,
        current_user=MagicMock(),
    )

    assert "suggestions" in result
    assert len(result["suggestions"]) >= 1
    assert result["suggestions"][0]["similarity_score"] > 0


# ─── auth.py line 115: list_users エンドポイント ─────────────────────────────


async def test_list_users_returns_all_users():
    """list_users: 管理者が全ユーザーを取得（line 115）"""
    from src.api.v1.auth import list_users

    user1 = MagicMock()
    user1.username = "admin"
    user2 = MagicMock()
    user2.username = "operator"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [user1, user2]
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    result = await list_users(db=db, current_user=MagicMock())

    assert len(result) == 2
    db.execute.assert_called_once()


async def test_list_users_empty_returns_empty_list():
    """list_users: ユーザーなし → 空リスト"""
    from src.api.v1.auth import list_users

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    result = await list_users(db=db, current_user=MagicMock())

    assert result == []


# ─── ai.py line 275: ai_status エンドポイント ────────────────────────────────


async def test_ai_status_returns_provider_info():
    """ai_status: provider/model/configured を返す（line 275）"""
    from src.api.v1.ai import ai_status

    with patch("src.api.v1.ai.ai_service") as mock_ai:
        mock_ai.provider = "openai"
        mock_ai.model = "gpt-4"
        mock_ai.api_key = "sk-test"

        result = await ai_status(current_user=MagicMock())

    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4"
    assert result["configured"] is True


async def test_ai_status_not_configured():
    """ai_status: api_key が空 → configured=False"""
    from src.api.v1.ai import ai_status

    with patch("src.api.v1.ai.ai_service") as mock_ai:
        mock_ai.provider = "none"
        mock_ai.model = "keyword"
        mock_ai.api_key = ""

        result = await ai_status(current_user=MagicMock())

    assert result["configured"] is False
