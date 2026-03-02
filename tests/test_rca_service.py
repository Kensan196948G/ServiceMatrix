"""RCAサービステスト - パターンマッチング・類似インシデント検索・推奨アクション生成"""
import uuid
from datetime import UTC, datetime

import pytest

from src.models.incident import Incident
from src.models.problem import Problem
from src.services.rca_service import RCAService

# ─── フィクスチャ ──────────────────────────────────────────────────────────


@pytest.fixture
def svc() -> RCAService:
    return RCAService()


# ─── カテゴリ判定テスト ────────────────────────────────────────────────────


def test_rca_categorize_infrastructure(svc):
    """infrastructureキーワード → Infrastructure カテゴリ"""
    category, confidence = svc._categorize_cause("server cpu high memory usage")
    assert category == "Infrastructure"
    assert confidence > 0.0


def test_rca_categorize_application(svc):
    """deploy/releaseキーワード → Application カテゴリ"""
    category, confidence = svc._categorize_cause("deploy release api service failed")
    assert category == "Application"
    assert confidence > 0.0


def test_rca_categorize_network(svc):
    """network/timeoutキーワード → Network カテゴリ"""
    category, confidence = svc._categorize_cause("network timeout connection refused")
    assert category == "Network"
    assert confidence > 0.0


def test_rca_categorize_security(svc):
    """securityキーワード → Security カテゴリ"""
    category, confidence = svc._categorize_cause("security breach unauthorized access attack")
    assert category == "Security"
    assert confidence > 0.0


# ─── 推奨アクション生成テスト ──────────────────────────────────────────────


def test_rca_generate_recommendations_infrastructure(svc):
    """Infrastructure → 推奨アクション3件を返す"""
    recs = svc._generate_recommendations("Infrastructure")
    assert len(recs) == 3
    assert all(isinstance(r, str) for r in recs)


# ─── 類似インシデント検索テスト ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rca_find_similar_incidents(db_session):
    """類似インシデント検索 - マッチするものを返す"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-{uuid.uuid4().hex[:8]}",
        title="server memory exhausted critical",
        priority="P1",
        status="New",
        created_at=now,
        updated_at=now,
    )
    db_session.add(incident)
    await db_session.flush()

    svc = RCAService()
    results = await svc.find_similar_incidents(db_session, "server memory high")
    incident_numbers = [i.incident_number for i in results]
    assert incident.incident_number in incident_numbers


# ─── analyze_problem テスト ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rca_analyze_problem_empty_incidents(db_session):
    """インシデントなし → Unknownカテゴリで結果返却（もしくは何らかの候補）"""
    now = datetime.now(UTC)
    problem = Problem(
        problem_id=uuid.uuid4(),
        problem_number=f"PRB-{uuid.uuid4().hex[:8]}",
        title="xyz unknown issue",
        status="New",
        priority="P3",
        known_error=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(problem)
    await db_session.flush()

    svc = RCAService()
    result = await svc.analyze_problem(db_session, str(problem.problem_id))

    assert result.problem_id == str(problem.problem_id)
    assert len(result.candidates) == 1
    assert result.candidates[0].cause_category == "Unknown"


@pytest.mark.asyncio
async def test_rca_analyze_problem_with_incidents(db_session):
    """インシデントありのProblem → 分析結果に類似インシデントが含まれる"""
    now = datetime.now(UTC)
    tag = uuid.uuid4().hex[:6]

    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-{tag}",
        title=f"deploy {tag} api service failure",
        priority="P2",
        status="New",
        created_at=now,
        updated_at=now,
    )
    db_session.add(incident)

    problem = Problem(
        problem_id=uuid.uuid4(),
        problem_number=f"PRB-{tag}",
        title=f"deploy {tag} api service failure recurring",
        status="Under_Investigation",
        priority="P2",
        known_error=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(problem)
    await db_session.flush()

    svc = RCAService()
    result = await svc.analyze_problem(db_session, str(problem.problem_id))

    assert result.problem_id == str(problem.problem_id)
    assert len(result.candidates) >= 1
    assert incident.incident_number in result.similar_incidents
