"""変更影響分析サービス・APIエンドポイント テスト"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.models.change import Change
from src.models.cmdb import ConfigurationItem
from src.services.change_impact_service import ChangeImpactResult, ChangeImpactService

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ─────────────────────────────────────────────────────────────────

async def _create_change(db_session, **kwargs) -> Change:
    now = datetime.now(UTC)
    defaults = {
        "change_id": uuid.uuid4(),
        "change_number": f"CHG-IMP-{uuid.uuid4().hex[:6].upper()}",
        "title": "database server upgrade maintenance",
        "description": "詳細な変更内容の説明。50文字以上の十分な記述をここに含めます。",
        "change_type": "Normal",
        "status": "Approved",
        "risk_score": 50,
        "risk_level": "Medium",
        "test_plan": "テスト計画あり",
        "rollback_plan": "ロールバック計画あり",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    change = Change(**defaults)
    db_session.add(change)
    await db_session.flush()
    return change


async def _create_ci(db_session, ci_name: str, ci_type: str = "Server") -> ConfigurationItem:
    now = datetime.now(UTC)
    ci = ConfigurationItem(
        ci_id=uuid.uuid4(),
        ci_name=ci_name,
        ci_type=ci_type,
        status="Active",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ci)
    await db_session.flush()
    return ci


# ─── ChangeImpactService 単体テスト ───────────────────────────────────────────

async def test_analyze_impact_returns_result(db_session):
    """正常系: analyze_impact がChangeImpactResultを返す"""
    change = await _create_change(db_session, risk_score=60)
    svc = ChangeImpactService()
    result = await svc.analyze_impact(db_session, str(change.change_id))

    assert isinstance(result, ChangeImpactResult)
    assert result.change_id == str(change.change_id)
    assert result.risk_level == "High"
    assert result.risk_score == pytest.approx(0.6)


async def test_analyze_impact_risk_levels(db_session):
    """risk_score別にrisk_levelが正しく設定される"""
    svc = ChangeImpactService()

    for score, expected_level in [(80, "Critical"), (65, "High"), (50, "Medium"), (20, "Low")]:
        change = await _create_change(db_session, risk_score=score)
        result = await svc.analyze_impact(db_session, str(change.change_id))
        assert result.risk_level == expected_level, f"score={score} should be {expected_level}"


async def test_analyze_impact_default_risk_score_when_zero(db_session):
    """risk_score=0の場合、デフォルト0.5が使われる"""
    change = await _create_change(db_session, risk_score=0, risk_level=None)
    svc = ChangeImpactService()
    result = await svc.analyze_impact(db_session, str(change.change_id))

    assert result.risk_score == pytest.approx(0.5)
    assert result.risk_level == "Medium"


async def test_analyze_impact_not_found(db_session):
    """存在しないchange_id → ValueErrorが発生"""
    svc = ChangeImpactService()
    with pytest.raises(ValueError, match="Change not found"):
        await svc.analyze_impact(db_session, str(uuid.uuid4()))


async def test_analyze_impact_finds_affected_cis(db_session):
    """タイトルのキーワードにマッチするCIが返される"""
    ci = await _create_ci(db_session, ci_name="database-server-01", ci_type="Server")
    change = await _create_change(db_session, title="database server maintenance")
    svc = ChangeImpactService()
    result = await svc.analyze_impact(db_session, str(change.change_id))

    ci_ids = [c["ci_id"] for c in result.affected_cis]
    assert str(ci.ci_id) in ci_ids
    for ci_entry in result.affected_cis:
        assert "ci_id" in ci_entry
        assert "name" in ci_entry
        assert "ci_type" in ci_entry


async def test_analyze_impact_affected_cis_max_5(db_session):
    """影響CIは最大5件"""
    for i in range(8):
        await _create_ci(db_session, ci_name=f"network-switch-{i:02d}", ci_type="Network")
    change = await _create_change(db_session, title="network switch upgrade")
    svc = ChangeImpactService()
    result = await svc.analyze_impact(db_session, str(change.change_id))

    assert len(result.affected_cis) <= 5


async def test_analyze_impact_conflicting_changes(db_session):
    """±3日以内の他のChangeが競合として検出される"""
    now = datetime.now(UTC)
    scheduled = now + timedelta(days=1)
    main_change = await _create_change(
        db_session, title="main scheduled change", scheduled_start_at=scheduled
    )
    conflict = await _create_change(
        db_session,
        title="conflicting change nearby",
        scheduled_start_at=scheduled + timedelta(hours=6),
    )
    svc = ChangeImpactService()
    result = await svc.analyze_impact(db_session, str(main_change.change_id))

    conflict_ids = [c["change_id"] for c in result.conflicting_changes]
    assert str(conflict.change_id) in conflict_ids


async def test_analyze_impact_no_conflict_outside_window(db_session):
    """±3日超の変更は競合に含まれない"""
    now = datetime.now(UTC)
    scheduled = now + timedelta(days=1)
    main_change = await _create_change(
        db_session, title="main scheduled change far", scheduled_start_at=scheduled
    )
    _far_change = await _create_change(
        db_session,
        title="far away change",
        scheduled_start_at=scheduled + timedelta(days=10),
    )
    svc = ChangeImpactService()
    result = await svc.analyze_impact(db_session, str(main_change.change_id))

    conflict_ids = [c["change_id"] for c in result.conflicting_changes]
    assert str(_far_change.change_id) not in conflict_ids


async def test_analyze_impact_logs_ai_decision(db_session):
    """analyze_impact がAIDecisionLogServiceにrecordする"""
    from src.services.ai_decision_log_service import AIDecisionLogService

    mock_log_svc = AIDecisionLogService()
    change = await _create_change(db_session, risk_score=70)
    svc = ChangeImpactService()

    with patch(
        "src.services.change_impact_service.ai_decision_log_service",
        mock_log_svc,
    ):
        result = await svc.analyze_impact(db_session, str(change.change_id))

    decisions = await mock_log_svc.get_decisions(entity_id=str(change.change_id))
    assert len(decisions) == 1
    assert decisions[0].action == "change_impact"
    assert decisions[0].entity_type == "change"


async def test_analyze_impact_recommendations_no_rollback(db_session):
    """ロールバック計画なし → 推奨メッセージが含まれる"""
    change = await _create_change(db_session, rollback_plan=None, risk_score=40)
    svc = ChangeImpactService()
    result = await svc.analyze_impact(db_session, str(change.change_id))

    assert any("ロールバック" in r for r in result.recommendations)


async def test_score_to_level():
    """_score_to_level の境界値テスト"""
    svc = ChangeImpactService()
    assert svc._score_to_level(0.0) == "Low"
    assert svc._score_to_level(0.39) == "Low"
    assert svc._score_to_level(0.4) == "Medium"
    assert svc._score_to_level(0.59) == "Medium"
    assert svc._score_to_level(0.6) == "High"
    assert svc._score_to_level(0.79) == "High"
    assert svc._score_to_level(0.8) == "Critical"
    assert svc._score_to_level(1.0) == "Critical"


# ─── API エンドポイントテスト ─────────────────────────────────────────────────

async def test_post_change_impact_success(client, auth_headers, db_session):
    """POST /ai/change-impact/{id} → 200, 結果返却"""
    change = await _create_change(db_session, risk_score=75)
    resp = await client.post(
        f"/api/v1/ai/change-impact/{change.change_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["change_id"] == str(change.change_id)
    assert data["risk_level"] in ("Low", "Medium", "High", "Critical")
    assert 0.0 <= data["risk_score"] <= 1.0
    assert isinstance(data["affected_cis"], list)
    assert isinstance(data["conflicting_changes"], list)
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["analysis_reasoning"], str)


async def test_post_change_impact_not_found(client, auth_headers):
    """POST /ai/change-impact/{不在id} → 404"""
    resp = await client.post(
        f"/api/v1/ai/change-impact/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_post_change_impact_no_auth(client, db_session):
    """認証なし → 401"""
    change = await _create_change(db_session)
    resp = await client.post(f"/api/v1/ai/change-impact/{change.change_id}")
    assert resp.status_code == 401


async def test_get_change_impact_after_post(client, auth_headers, db_session):
    """POST後にGETで最新結果が取得できる"""
    change = await _create_change(db_session, risk_score=55)
    change_id = str(change.change_id)

    await client.post(f"/api/v1/ai/change-impact/{change_id}", headers=auth_headers)

    resp = await client.get(f"/api/v1/ai/change-impact/{change_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["change_id"] == change_id
    assert "output" in data
    assert "timestamp" in data


async def test_get_change_impact_not_found(client, auth_headers):
    """分析未実行のchange_id → 404"""
    resp = await client.get(
        f"/api/v1/ai/change-impact/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_get_change_impact_no_auth(client):
    """認証なし → 401"""
    resp = await client.get(f"/api/v1/ai/change-impact/{uuid.uuid4()}")
    assert resp.status_code == 401
