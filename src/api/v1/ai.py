"""AI機能API - トリアージ・類似検索・決定ログ"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.incident import Incident
from src.models.problem import Problem
from src.models.user import User
from src.services.agent_orchestrator import orchestrator
from src.services.ai_decision_log_service import AIDecision, ai_decision_log_service
from src.services.ai_service import ai_service
from src.services.ai_triage_service import ai_triage_service
from src.services.auto_repair_service import auto_repair_service
from src.services.change_impact_service import change_impact_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/triage/{incident_id}",
    summary="インシデントトリアージ実行",
    status_code=status.HTTP_200_OK,
)
async def triage_incident(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """指定インシデントにAIトリアージを実行し結果を返す"""
    result = await ai_triage_service.apply_triage_to_incident(db, incident_id)
    if result.confidence == 0.0 and result.priority == "Unknown":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    decision = AIDecision(
        action="triage",
        entity_type="incident",
        entity_id=incident_id,
        input_data={"incident_id": incident_id},
        output_data={
            "priority": result.priority,
            "category": result.category,
            "reasoning": result.reasoning,
        },
        confidence=result.confidence,
        provider="keyword",
    )
    await ai_decision_log_service.record(decision)

    return {
        "incident_id": incident_id,
        "priority": result.priority,
        "category": result.category,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }


@router.get(
    "/similar-incidents",
    summary="類似インシデント検索",
)
async def find_similar_incidents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    title: str = Query(..., description="検索タイトル"),
    description: str | None = Query(default=None, description="検索説明文"),
    limit: int = Query(default=5, ge=1, le=20),
) -> list[dict]:
    """TF-IDFベースの類似インシデント検索"""
    results = await ai_triage_service.find_similar_incidents(db, title, description, limit)

    decision = AIDecision(
        action="similar_search",
        entity_type="incident",
        entity_id="query",
        input_data={"title": title, "description": description, "limit": limit},
        output_data={"results_count": len(results)},
        confidence=1.0,
        provider="keyword",
    )
    await ai_decision_log_service.record(decision)

    return results


@router.get(
    "/decisions",
    summary="AI決定ログ一覧",
)
async def list_decisions(
    current_user: Annotated[User, Depends(get_current_user)],
    entity_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
) -> list[dict]:
    """AI決定ログの一覧を返す"""
    decisions = await ai_decision_log_service.get_decisions(entity_id=entity_id, action=action)
    return [
        {
            "action": d.action,
            "entity_type": d.entity_type,
            "entity_id": d.entity_id,
            "confidence": d.confidence,
            "provider": d.provider,
            "timestamp": d.timestamp.isoformat(),
        }
        for d in decisions
    ]


@router.get(
    "/decisions/summary",
    summary="AI決定サマリー",
)
async def decisions_summary(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """AI決定ログの集計サマリーを返す"""
    return await ai_decision_log_service.get_summary()


@router.post(
    "/change-impact/{change_id}",
    summary="変更影響分析実行",
    status_code=status.HTTP_200_OK,
)
async def analyze_change_impact(
    change_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """指定Changeの影響CI特定・競合チェック・リスク評価を実行"""
    try:
        result = await change_impact_service.analyze_impact(db, change_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "change_id": result.change_id,
        "risk_level": result.risk_level,
        "risk_score": result.risk_score,
        "affected_cis": result.affected_cis,
        "conflicting_changes": result.conflicting_changes,
        "recommendations": result.recommendations,
        "analysis_reasoning": result.analysis_reasoning,
    }


@router.get(
    "/change-impact/{change_id}",
    summary="最新の変更影響分析結果取得",
    status_code=status.HTTP_200_OK,
)
async def get_change_impact(
    change_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """指定ChangeのAI決定ログから最新の変更影響分析結果を返す"""
    decisions = await ai_decision_log_service.get_decisions(
        entity_id=change_id, action="change_impact"
    )
    if not decisions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No impact analysis found for change: {change_id}",
        )
    latest = max(decisions, key=lambda d: d.timestamp)
    return {
        "change_id": latest.entity_id,
        "output": latest.output_data,
        "confidence": latest.confidence,
        "provider": latest.provider,
        "timestamp": latest.timestamp.isoformat(),
    }


@router.post(
    "/auto-repair/{incident_id}",
    summary="自動修復候補分析実行",
    status_code=status.HTTP_200_OK,
)
async def analyze_auto_repair(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    title: str = Query(..., description="インシデントタイトル"),
    description: str | None = Query(default=None, description="インシデント詳細"),
) -> dict:
    """指定インシデントの修復候補を分析して返す"""
    analysis = await auto_repair_service.analyze(incident_id, title, description)
    return {
        "incident_id": analysis.incident_id,
        "symptoms": analysis.symptoms,
        "root_cause_hypothesis": analysis.root_cause_hypothesis,
        "candidates": [
            {
                "action": c.action,
                "description": c.description,
                "risk_level": c.risk_level,
                "confidence": c.confidence,
                "automated": c.automated,
                "steps": c.steps,
            }
            for c in analysis.candidates
        ],
        "recommended": {
            "action": analysis.recommended.action,
            "description": analysis.recommended.description,
            "risk_level": analysis.recommended.risk_level,
            "confidence": analysis.recommended.confidence,
            "automated": analysis.recommended.automated,
        }
        if analysis.recommended
        else None,
        "analyzed_at": analysis.analyzed_at.isoformat(),
    }


@router.post(
    "/auto-repair/{incident_id}/execute",
    summary="低リスク修復自動実行（シミュレーション）",
    status_code=status.HTTP_200_OK,
)
async def execute_auto_repair(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    title: str = Query(..., description="インシデントタイトル"),
    description: str | None = Query(default=None, description="インシデント詳細"),
) -> dict:
    """低リスク修復アクションをシミュレーション実行する"""
    result = await auto_repair_service.execute_low_risk(incident_id, title, description)
    return result


@router.post(
    "/orchestrate/{incident_id}",
    summary="Agent Teamsオーケストレーション実行",
    status_code=status.HTTP_200_OK,
)
async def orchestrate_incident(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    title: str = Query(..., description="インシデントタイトル"),
    description: str | None = Query(default=None, description="インシデント詳細"),
) -> dict:
    """インシデント複雑度を判定し、適切なAgent Teamsを動的構成して実行する"""
    team_result = await orchestrator.orchestrate(db, incident_id, title, description)
    return {
        "task_id": team_result.task_id,
        "complexity": team_result.complexity,
        "agents_used": team_result.agents_used,
        "results": team_result.results,
        "total_confidence": team_result.total_confidence,
        "executed_at": team_result.executed_at,
    }


# ─── Step27: GPT-4/Claude AI強化エンドポイント ────────────────────────────


@router.get(
    "/status",
    summary="AI設定ステータス確認",
)
async def ai_status(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """AI設定ステータス（プロバイダー・モデル・設定済みか）"""
    return {
        "provider": ai_service.provider,
        "model": ai_service.model,
        "configured": bool(ai_service.api_key),
        "mode": "mock" if (ai_service.provider == "mock" or not ai_service.api_key) else "live",
    }


@router.post(
    "/incidents/{incident_id}/summarize",
    summary="インシデント要約生成",
    status_code=status.HTTP_200_OK,
)
async def summarize_incident(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """インシデントの内容をAIで要約する"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )

    summary = await ai_service.summarize_incident(
        incident_title=incident.title,
        description=incident.description or "",
        comments=[],
    )
    return {"incident_id": incident_id, "summary": summary}


@router.post(
    "/incidents/{incident_id}/suggest-priority",
    summary="インシデント優先度提案",
    status_code=status.HTTP_200_OK,
)
async def suggest_incident_priority(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """インシデントの優先度をAIで提案する"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )

    priority = await ai_service.suggest_incident_priority(
        title=incident.title,
        description=incident.description or "",
        affected_service=getattr(incident, "affected_service", None),
    )
    return {"incident_id": incident_id, "suggested_priority": priority}


@router.post(
    "/problems/{problem_id}/generate-rca",
    summary="RCAレポート生成",
    status_code=status.HTTP_200_OK,
)
async def generate_rca_report(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """問題の根本原因分析レポートをAIで生成する"""
    result = await db.execute(select(Problem).where(Problem.problem_id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問題が見つかりません")

    affected_services: list[str] = []
    affected_service = getattr(problem, "affected_service", None)
    if affected_service:
        affected_services = [affected_service]

    rca = await ai_service.generate_rca_report(
        problem_title=problem.title,
        affected_services=affected_services,
        timeline=[],
    )
    return {"problem_id": problem_id, **rca}
