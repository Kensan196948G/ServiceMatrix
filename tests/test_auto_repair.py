"""自動修復Agentサービス・AgentOrchestrator テスト"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.services.auto_repair_service import AutoRepairService, RepairCandidate, RepairAnalysis
from src.services.agent_orchestrator import AgentOrchestrator, TaskComplexity

pytestmark = pytest.mark.asyncio


# ─── フィクスチャ ─────────────────────────────────────────────────────────────

@pytest.fixture
def svc():
    return AutoRepairService()


@pytest.fixture
def orch():
    return AgentOrchestrator()


# ─── 症状抽出テスト ───────────────────────────────────────────────────────────

def test_extract_symptoms_timeout(svc):
    """'timeout' キーワード → timeout 症状検出"""
    symptoms = svc._extract_symptoms("database connection timeout")
    assert "timeout" in symptoms


def test_extract_symptoms_error(svc):
    """'error' キーワード → error 症状検出"""
    symptoms = svc._extract_symptoms("service failed with error 500")
    assert "error" in symptoms


def test_extract_symptoms_outage(svc):
    """'outage/down' キーワード → outage 症状検出"""
    symptoms = svc._extract_symptoms("production is down complete outage")
    assert "outage" in symptoms


def test_extract_symptoms_performance(svc):
    """'slow/latency' キーワード → performance 症状検出"""
    symptoms = svc._extract_symptoms("api response is very slow high latency")
    assert "performance" in symptoms


def test_extract_symptoms_multiple(svc):
    """複数キーワード → 複数症状検出"""
    symptoms = svc._extract_symptoms("production down with timeout errors")
    assert "outage" in symptoms
    assert "timeout" in symptoms
    assert "error" in symptoms


def test_extract_symptoms_no_match(svc):
    """無関係テキスト → 空リスト"""
    symptoms = svc._extract_symptoms("routine maintenance scheduled for next week")
    assert symptoms == []


# ─── 修復候補生成テスト ────────────────────────────────────────────────────────

def test_get_candidates_timeout(svc):
    """timeout症状 → clear_cache/scale_up候補が含まれる"""
    candidates = svc._get_candidates(["timeout"])
    actions = [c.action for c in candidates]
    assert "clear_cache" in actions or "scale_up" in actions


def test_get_candidates_outage(svc):
    """outage症状 → restart_service候補が含まれる"""
    candidates = svc._get_candidates(["outage"])
    actions = [c.action for c in candidates]
    assert "restart_service" in actions


def test_get_candidates_empty_symptoms_returns_manual(svc):
    """症状なし → manual候補が返る"""
    candidates = svc._get_candidates([])
    assert len(candidates) == 1
    assert candidates[0].action == "manual"


def test_get_candidates_no_duplicates(svc):
    """複数の症状に同じアクションが含まれても重複なし"""
    candidates = svc._get_candidates(["error", "outage"])
    actions = [c.action for c in candidates]
    assert len(actions) == len(set(actions))


# ─── 最優先候補選択テスト ─────────────────────────────────────────────────────

def test_select_best_candidate_highest_confidence(svc):
    """最高信頼度の候補が選択される"""
    candidates = [
        RepairCandidate("a", "desc_a", "low", 0.6, True),
        RepairCandidate("b", "desc_b", "low", 0.9, True),
        RepairCandidate("c", "desc_c", "low", 0.7, False),
    ]
    best = svc._select_best_candidate(candidates)
    assert best is not None
    assert best.action == "b"
    assert best.confidence == 0.9


def test_select_best_candidate_empty(svc):
    """空リスト → None"""
    assert svc._select_best_candidate([]) is None


def test_select_best_candidate_prefers_low_risk_on_tie(svc):
    """同信頼度の場合はリスクが低い方が選ばれる"""
    candidates = [
        RepairCandidate("high_risk", "desc", "high", 0.8, False),
        RepairCandidate("low_risk", "desc", "low", 0.8, True),
    ]
    best = svc._select_best_candidate(candidates)
    assert best is not None
    assert best.action == "low_risk"


# ─── 根本原因仮説テスト ────────────────────────────────────────────────────────

def test_hypothesize_root_cause_outage(svc):
    """outage症状 → 停止関連の仮説"""
    hypothesis = svc._hypothesize_root_cause(["outage"], "production down")
    assert "停止" in hypothesis or "デプロイ" in hypothesis


def test_hypothesize_root_cause_no_symptoms(svc):
    """症状なし → 不明メッセージ"""
    hypothesis = svc._hypothesize_root_cause([], "")
    assert "不明" in hypothesis or "調査" in hypothesis


# ─── AutoRepairService 統合テスト ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_returns_repair_analysis(svc):
    """analyze() → RepairAnalysis が返る"""
    incident_id = str(uuid.uuid4())
    result = await svc.analyze(incident_id, "database timeout error", "connection pool exhausted")
    assert isinstance(result, RepairAnalysis)
    assert result.incident_id == incident_id
    assert len(result.candidates) > 0
    assert result.recommended is not None


@pytest.mark.asyncio
async def test_analyze_logs_ai_decision(svc):
    """analyze() → AIDecisionLogに記録される"""
    from src.services.ai_decision_log_service import ai_decision_log_service

    incident_id = str(uuid.uuid4())
    await svc.analyze(incident_id, "service error", None)
    decisions = await ai_decision_log_service.get_decisions(entity_id=incident_id)
    assert len(decisions) >= 1
    assert decisions[0].action == "auto_repair"
    assert decisions[0].provider == "rule_based"


@pytest.mark.asyncio
async def test_execute_low_risk_returns_executed_and_skipped(svc):
    """execute_low_risk() → executed/skipped が分類される"""
    incident_id = str(uuid.uuid4())
    result = await svc.execute_low_risk(incident_id, "service timeout", "response timed out")
    assert "executed" in result
    assert "skipped" in result
    assert result["simulation"] is True
    assert result["incident_id"] == incident_id
    # 低リスク自動実行候補はexecutedに
    for item in result["executed"]:
        assert item["simulated"] is True


@pytest.mark.asyncio
async def test_execute_low_risk_high_risk_skipped(svc):
    """高リスク候補はexecutedに含まれない"""
    incident_id = str(uuid.uuid4())
    result = await svc.execute_low_risk(
        incident_id, "production down critical outage", "entire service unavailable"
    )
    # rollbackはhigh riskなのでskipped
    skipped_actions = [s["action"] for s in result["skipped"]]
    assert "rollback" in skipped_actions


# ─── AgentOrchestrator 複雑度判定テスト ──────────────────────────────────────

def test_assess_complexity_simple(orch):
    """一般テキスト → SIMPLE"""
    assert orch._assess_complexity("routine check", None) == TaskComplexity.SIMPLE


def test_assess_complexity_moderate(orch):
    """エラーキーワード → MODERATE"""
    assert orch._assess_complexity("service error occurred", None) == TaskComplexity.MODERATE


def test_assess_complexity_complex(orch):
    """outage/down キーワード → COMPLEX"""
    assert orch._assess_complexity("production is down", None) == TaskComplexity.COMPLEX


def test_assess_complexity_complex_japanese(orch):
    """日本語障害キーワード → COMPLEX"""
    assert orch._assess_complexity("本番環境で障害が発生", None) == TaskComplexity.COMPLEX


# ─── AgentOrchestrator orchestrate テスト ────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrate_simple_uses_only_triage(orch, db_session):
    """SIMPLE → トリアージのみ実行"""
    result = await orch.orchestrate(
        db_session, str(uuid.uuid4()), "scheduled maintenance notification", None
    )
    assert result.complexity == TaskComplexity.SIMPLE
    assert "ai_triage" in result.agents_used
    assert "auto_repair" not in result.agents_used
    assert "triage" in result.results


@pytest.mark.asyncio
async def test_orchestrate_moderate_includes_repair(orch, db_session):
    """MODERATE → トリアージ + 修復候補分析"""
    result = await orch.orchestrate(
        db_session, str(uuid.uuid4()), "application error on login page", None
    )
    assert result.complexity == TaskComplexity.MODERATE
    assert "ai_triage" in result.agents_used
    assert "auto_repair" in result.agents_used
    assert "repair_analysis" in result.results


@pytest.mark.asyncio
async def test_orchestrate_complex_includes_auto_executable(orch, db_session):
    """COMPLEX → トリアージ + 修復候補 + 自動実行候補"""
    result = await orch.orchestrate(
        db_session, str(uuid.uuid4()), "production database down critical outage", None
    )
    assert result.complexity == TaskComplexity.COMPLEX
    assert "auto_repair_executor" in result.agents_used
    assert "auto_executable" in result.results
    assert isinstance(result.results["auto_executable"], list)


@pytest.mark.asyncio
async def test_orchestrate_total_confidence_in_range(orch, db_session):
    """total_confidence が 0.0-1.0 の範囲内"""
    result = await orch.orchestrate(
        db_session, str(uuid.uuid4()), "network timeout error", None
    )
    assert 0.0 <= result.total_confidence <= 1.0


# ─── API エンドポイントテスト ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_repair_analyze_endpoint(client, auth_headers):
    """POST /ai/auto-repair/{id} → 200, 修復候補レスポンス"""
    incident_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/ai/auto-repair/{incident_id}",
        params={"title": "database timeout error", "description": "connection pool exhausted"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == incident_id
    assert isinstance(data["symptoms"], list)
    assert isinstance(data["candidates"], list)
    assert len(data["candidates"]) > 0
    assert "root_cause_hypothesis" in data
    assert "analyzed_at" in data


@pytest.mark.asyncio
async def test_auto_repair_analyze_no_auth(client):
    """認証なし → 401"""
    resp = await client.post(
        f"/api/v1/ai/auto-repair/{uuid.uuid4()}",
        params={"title": "test error"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auto_repair_analyze_missing_title(client, auth_headers):
    """titleなし → 422"""
    resp = await client.post(
        f"/api/v1/ai/auto-repair/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_auto_repair_execute_endpoint(client, auth_headers):
    """POST /ai/auto-repair/{id}/execute → 200, シミュレーション結果"""
    incident_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/ai/auto-repair/{incident_id}/execute",
        params={"title": "service timeout detected"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == incident_id
    assert data["simulation"] is True
    assert "executed" in data
    assert "skipped" in data


@pytest.mark.asyncio
async def test_auto_repair_execute_no_auth(client):
    """認証なし → 401"""
    resp = await client.post(
        f"/api/v1/ai/auto-repair/{uuid.uuid4()}/execute",
        params={"title": "test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_orchestrate_endpoint(client, auth_headers):
    """POST /ai/orchestrate/{id} → 200, AgentTeamResult"""
    incident_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/ai/orchestrate/{incident_id}",
        params={"title": "production down critical outage"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == incident_id
    assert data["complexity"] == "complex"
    assert "ai_triage" in data["agents_used"]
    assert "results" in data
    assert 0.0 <= data["total_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_orchestrate_endpoint_simple(client, auth_headers):
    """SIMPLE複雑度 → triage のみ実行"""
    incident_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/ai/orchestrate/{incident_id}",
        params={"title": "scheduled maintenance notification"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["complexity"] == "simple"
    assert data["agents_used"] == ["ai_triage"]


@pytest.mark.asyncio
async def test_orchestrate_endpoint_no_auth(client):
    """認証なし → 401"""
    resp = await client.post(
        f"/api/v1/ai/orchestrate/{uuid.uuid4()}",
        params={"title": "test"},
    )
    assert resp.status_code == 401
