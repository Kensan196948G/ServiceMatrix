"""ai.py / notification_service.py 直接呼び出しテスト - カバレッジ向上

対象: src/api/v1/ai.py (69%), src/services/notification_service.py (77%)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _make_incident_mock(incident_id=None, title="テストインシデント"):
    inc = MagicMock()
    inc.incident_id = incident_id or str(uuid.uuid4())
    inc.title = title
    inc.description = "インシデント説明"
    return inc


def _make_problem_mock(problem_id=None, title="テスト問題"):
    prob = MagicMock()
    prob.problem_id = problem_id or str(uuid.uuid4())
    prob.title = title
    prob.description = "問題説明"
    prob.affected_service = None
    return prob


# ─── ai.py: find_similar_incidents (lines 77, 86, 88) ─────────────────────────


async def test_find_similar_incidents_returns_results():
    """find_similar_incidents: 類似検索結果を返す（lines 77, 86, 88）"""
    from src.api.v1.ai import find_similar_incidents

    db = AsyncMock()
    current_user = MagicMock()

    similar_results = [
        {"incident_id": str(uuid.uuid4()), "title": "類似インシデント", "score": 0.85}
    ]

    with patch("src.api.v1.ai.ai_triage_service") as mock_triage:
        mock_triage.find_similar_incidents = AsyncMock(return_value=similar_results)
        with patch("src.api.v1.ai.ai_decision_log_service") as mock_log:
            mock_log.record = AsyncMock()
            result = await find_similar_incidents(
                db=db,
                current_user=current_user,
                title="ネットワーク障害",
                description="接続できない",
                limit=5,
            )

    assert result == similar_results
    mock_log.record.assert_called_once()


async def test_find_similar_incidents_empty_results():
    """find_similar_incidents: 結果なし → 空リスト"""
    from src.api.v1.ai import find_similar_incidents

    db = AsyncMock()
    current_user = MagicMock()

    with patch("src.api.v1.ai.ai_triage_service") as mock_triage:
        mock_triage.find_similar_incidents = AsyncMock(return_value=[])
        with patch("src.api.v1.ai.ai_decision_log_service") as mock_log:
            mock_log.record = AsyncMock()
            result = await find_similar_incidents(
                db=db,
                current_user=current_user,
                title="存在しないインシデント",
                description=None,
                limit=3,
            )

    assert result == []
    mock_log.record.assert_called_once()


# ─── ai.py: list_decisions (lines 139-142) ────────────────────────────────────


async def test_list_decisions_returns_list():
    """list_decisions: AI決定ログ一覧を返す（lines 139-142）"""
    from src.api.v1.ai import list_decisions
    from datetime import UTC, datetime

    current_user = MagicMock()

    decision_mock = MagicMock()
    decision_mock.action = "triage"
    decision_mock.entity_type = "incident"
    decision_mock.entity_id = "INC-001"
    decision_mock.confidence = 0.9
    decision_mock.provider = "mock"
    decision_mock.timestamp = datetime.now(UTC)

    with patch("src.api.v1.ai.ai_decision_log_service") as mock_log:
        mock_log.get_decisions = AsyncMock(return_value=[decision_mock])
        result = await list_decisions(
            current_user=current_user,
            entity_id=None,
            action=None,
        )

    assert len(result) == 1
    assert result[0]["action"] == "triage"
    assert result[0]["entity_type"] == "incident"
    assert "timestamp" in result[0]


async def test_decisions_summary_returns_dict():
    """decisions_summary: サマリーを返す（line 142）"""
    from src.api.v1.ai import decisions_summary

    current_user = MagicMock()
    summary_data = {"total": 10, "by_action": {"triage": 5, "similar_search": 5}}

    with patch("src.api.v1.ai.ai_decision_log_service") as mock_log:
        mock_log.get_summary = AsyncMock(return_value=summary_data)
        result = await decisions_summary(current_user=current_user)

    assert result == summary_data


# ─── ai.py: analyze_change_impact (line 275) ──────────────────────────────────


async def test_analyze_change_impact_value_error_raises_404():
    """analyze_change_impact: ValueError → 404（line 275）"""
    from src.api.v1.ai import analyze_change_impact

    db = AsyncMock()
    current_user = MagicMock()

    with patch("src.api.v1.ai.change_impact_service") as mock_svc:
        mock_svc.analyze_impact = AsyncMock(side_effect=ValueError("Change not found"))
        with pytest.raises(HTTPException) as exc_info:
            await analyze_change_impact(
                change_id=str(uuid.uuid4()),
                db=db,
                current_user=current_user,
            )

    assert exc_info.value.status_code == 404


async def test_analyze_change_impact_success():
    """analyze_change_impact: 正常 → 分析結果を返す"""
    from src.api.v1.ai import analyze_change_impact

    db = AsyncMock()
    current_user = MagicMock()

    impact_result = MagicMock()
    impact_result.change_id = "CHG-001"
    impact_result.risk_level = "Medium"
    impact_result.risk_score = 45
    impact_result.affected_cis = []
    impact_result.conflicting_changes = []
    impact_result.recommendations = ["テスト推奨"]
    impact_result.analysis_reasoning = "分析理由"

    with patch("src.api.v1.ai.change_impact_service") as mock_svc:
        mock_svc.analyze_impact = AsyncMock(return_value=impact_result)
        result = await analyze_change_impact(
            change_id="CHG-001",
            db=db,
            current_user=current_user,
        )

    assert result["change_id"] == "CHG-001"
    assert result["risk_level"] == "Medium"


# ─── ai.py: summarize_incident (lines 294-306) ────────────────────────────────


async def test_summarize_incident_not_found_raises_404():
    """summarize_incident: インシデント不存在 → 404（lines 294-297）"""
    from src.api.v1.ai import summarize_incident

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(None))
    current_user = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await summarize_incident(
            incident_id=str(uuid.uuid4()),
            db=db,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404


async def test_summarize_incident_success():
    """summarize_incident: 正常 → summary を含む dict を返す（lines 301, 306）"""
    from src.api.v1.ai import summarize_incident

    incident_id = str(uuid.uuid4())
    inc = _make_incident_mock(incident_id=incident_id, title="ネットワーク障害")
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(inc))
    current_user = MagicMock()

    with patch("src.api.v1.ai.ai_service") as mock_ai:
        mock_ai.summarize_incident = AsyncMock(return_value="ネットワーク障害のまとめ")
        result = await summarize_incident(
            incident_id=incident_id,
            db=db,
            current_user=current_user,
        )

    assert result["incident_id"] == incident_id
    assert result["summary"] == "ネットワーク障害のまとめ"


# ─── ai.py: suggest_incident_priority (lines 320-332) ────────────────────────


async def test_suggest_incident_priority_not_found_raises_404():
    """suggest_incident_priority: インシデント不存在 → 404（lines 320-323）"""
    from src.api.v1.ai import suggest_incident_priority

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(None))

    with pytest.raises(HTTPException) as exc_info:
        await suggest_incident_priority(
            incident_id=str(uuid.uuid4()),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_suggest_incident_priority_success():
    """suggest_incident_priority: 正常 → suggested_priority を返す（lines 327, 332）"""
    from src.api.v1.ai import suggest_incident_priority

    incident_id = str(uuid.uuid4())
    inc = _make_incident_mock(incident_id=incident_id)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(inc))

    with patch("src.api.v1.ai.ai_service") as mock_ai:
        mock_ai.suggest_incident_priority = AsyncMock(return_value="P1")
        result = await suggest_incident_priority(
            incident_id=incident_id,
            db=db,
            current_user=MagicMock(),
        )

    assert result["incident_id"] == incident_id
    assert result["suggested_priority"] == "P1"


# ─── ai.py: generate_rca_report (lines 346-361) ───────────────────────────────


async def test_generate_rca_report_not_found_raises_404():
    """generate_rca_report: 問題不存在 → 404（lines 346-349）"""
    from src.api.v1.ai import generate_rca_report

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(None))

    with pytest.raises(HTTPException) as exc_info:
        await generate_rca_report(
            problem_id=str(uuid.uuid4()),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_generate_rca_report_success_no_affected_service():
    """generate_rca_report: 正常(affected_service=None) → rca 返却（lines 351-361）"""
    from src.api.v1.ai import generate_rca_report

    problem_id = str(uuid.uuid4())
    prob = _make_problem_mock(problem_id=problem_id)
    prob.affected_service = None  # None branch

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(prob))

    rca_data = {"summary": "根本原因はXです", "recommendations": ["対策A"]}
    with patch("src.api.v1.ai.ai_service") as mock_ai:
        mock_ai.generate_rca_report = AsyncMock(return_value=rca_data)
        result = await generate_rca_report(
            problem_id=problem_id,
            db=db,
            current_user=MagicMock(),
        )

    assert result["problem_id"] == problem_id
    assert result["summary"] == "根本原因はXです"


async def test_generate_rca_report_success_with_affected_service():
    """generate_rca_report: affected_service あり → affected_services リストに含む（lines 352-354）"""
    from src.api.v1.ai import generate_rca_report

    problem_id = str(uuid.uuid4())
    prob = _make_problem_mock(problem_id=problem_id)
    prob.affected_service = "OrderService"  # non-None branch

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(prob))

    rca_data = {"summary": "OrderServiceの根本原因", "recommendations": []}
    with patch("src.api.v1.ai.ai_service") as mock_ai:
        mock_ai.generate_rca_report = AsyncMock(return_value=rca_data)
        result = await generate_rca_report(
            problem_id=problem_id,
            db=db,
            current_user=MagicMock(),
        )

    assert result["problem_id"] == problem_id
    # generate_rca_report が affected_services=["OrderService"] で呼ばれたことを確認
    call_kwargs = mock_ai.generate_rca_report.call_args.kwargs
    assert "OrderService" in call_kwargs.get("affected_services", [])


# ─── notification_service.py: GitHub API呼び出し分岐 ──────────────────────────


async def test_create_incident_github_issue_no_token_returns_none():
    """create_incident_github_issue: トークンなし → None（line 52）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = None
        mock_settings.github_repo = "owner/repo"
        result = await notification_service.create_incident_github_issue(
            incident_number="INC-2026-000001",
            incident_title="テストインシデント",
            priority="P1",
        )

    assert result is None


async def test_create_incident_github_issue_success():
    """create_incident_github_issue: 成功 → issue_number を返す（lines 84-85）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_test"
        mock_settings.github_repo = "owner/repo"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"number": 42}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.create_incident_github_issue(
                incident_number="INC-2026-000001",
                incident_title="テスト",
                priority="P1",
            )

    assert result == 42


async def test_create_incident_github_issue_exception_returns_none():
    """create_incident_github_issue: 例外 → None（line 90）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_test"
        mock_settings.github_repo = "owner/repo"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("Network error"))

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.create_incident_github_issue(
                incident_number="INC-001",
                incident_title="テスト",
                priority="P1",
            )

    assert result is None


async def test_close_incident_github_issue_success():
    """close_incident_github_issue: 成功 → True（lines 113-114）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_test"
        mock_settings.github_repo = "owner/repo"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.patch = AsyncMock(return_value=mock_response)

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.close_incident_github_issue(
                github_issue_number=42,
                incident_number="INC-001",
            )

    assert result is True


async def test_close_incident_github_issue_no_token_returns_false():
    """close_incident_github_issue: トークンなし → False（line 106）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = None
        mock_settings.github_repo = "owner/repo"
        result = await notification_service.close_incident_github_issue(
            github_issue_number=1,
            incident_number="INC-001",
        )

    assert result is False


async def test_close_incident_github_issue_exception_returns_false():
    """close_incident_github_issue: 例外 → False（line 119）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_test"
        mock_settings.github_repo = "owner/repo"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.patch = AsyncMock(side_effect=Exception("Timeout"))

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.close_incident_github_issue(
                github_issue_number=42,
                incident_number="INC-001",
            )

    assert result is False


async def test_add_github_issue_comment_success():
    """add_github_issue_comment: 成功 → True（lines 143-144）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_test"
        mock_settings.github_repo = "owner/repo"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.add_github_issue_comment(
                github_issue_number=42,
                comment="テストコメント",
                incident_number="INC-001",
            )

    assert result is True


async def test_add_github_issue_comment_no_token_returns_false():
    """add_github_issue_comment: トークンなし → False（line 136）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = None
        mock_settings.github_repo = "owner/repo"
        result = await notification_service.add_github_issue_comment(
            github_issue_number=1,
            comment="コメント",
            incident_number="INC-001",
        )

    assert result is False


async def test_add_github_issue_comment_exception_returns_false():
    """add_github_issue_comment: 例外 → False（line 149）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.github_token = "ghp_test"
        mock_settings.github_repo = "owner/repo"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("API error"))

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.add_github_issue_comment(
                github_issue_number=42,
                comment="コメント",
                incident_number="INC-001",
            )

    assert result is False


async def test_notify_sla_warning_webhook_success():
    """notify_sla_warning: Webhook送信成功（lines 199-207）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.alert_webhook_enabled = True
        mock_settings.alert_webhook_url = "https://hooks.example.com/alert"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.notify_sla_warning(
                incident_number="INC-001",
                incident_title="テスト",
                priority="P1",
                warning_level="warning_70",
                progress_percent=70.0,
            )

    assert result.get("webhook") is not None
    assert result["webhook"]["status"] == "sent"


async def test_notify_sla_warning_webhook_disabled():
    """notify_sla_warning: Webhook無効 → 空 dict"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.alert_webhook_enabled = False
        mock_settings.alert_webhook_url = None

        result = await notification_service.notify_sla_warning(
            incident_number="INC-001",
            incident_title="テスト",
            priority="P2",
            warning_level="warning_90",
            progress_percent=90.0,
        )

    assert result == {}


async def test_notify_sla_warning_webhook_exception():
    """notify_sla_warning: Webhook例外 → results['webhook']=None（lines 214-216）"""
    from src.services.notification_service import notification_service

    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.alert_webhook_enabled = True
        mock_settings.alert_webhook_url = "https://hooks.example.com/alert"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("src.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await notification_service.notify_sla_warning(
                incident_number="INC-001",
                incident_title="テスト",
                priority="P1",
                warning_level="warning_90",
                progress_percent=90.0,
            )

    assert result.get("webhook") is None
