"""Agent Teamsオーケストレーター - タスク複雑度による動的Agent割当"""

from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.services.ai_triage_service import ai_triage_service
from src.services.auto_repair_service import auto_repair_service

logger = get_logger(__name__)

# キーワードしきい値
_COMPLEX_KEYWORDS = ["outage", "down", "critical", "production", "停止", "障害", "緊急"]
_MODERATE_KEYWORDS = ["error", "failed", "timeout", "performance", "エラー", "失敗", "遅延"]


class TaskComplexity(StrEnum):
    SIMPLE = "simple"  # キーワードトリアージのみ
    MODERATE = "moderate"  # トリアージ + 修復候補
    COMPLEX = "complex"  # トリアージ + 修復候補 + 自動実行候補抽出


@dataclass
class AgentTeamResult:
    task_id: str
    complexity: TaskComplexity
    agents_used: list[str]
    results: dict
    total_confidence: float
    executed_at: str = field(
        default_factory=lambda: (
            __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        )
    )


class AgentOrchestrator:
    """タスク複雑度に基づいてAIエージェントチームを動的構成"""

    def _assess_complexity(self, title: str, description: str | None) -> TaskComplexity:
        text = f"{title} {description or ''}".lower()
        if any(kw in text for kw in _COMPLEX_KEYWORDS):
            return TaskComplexity.COMPLEX
        if any(kw in text for kw in _MODERATE_KEYWORDS):
            return TaskComplexity.MODERATE
        return TaskComplexity.SIMPLE

    async def orchestrate(
        self,
        db: AsyncSession,
        incident_id: str,
        title: str,
        description: str | None,
    ) -> AgentTeamResult:
        """インシデントの複雑度を判定し、適切なエージェントチームを割り当て"""
        complexity = self._assess_complexity(title, description)
        results: dict = {}
        agents_used: list[str] = []
        confidences: list[float] = []

        # 常にトリアージ実行
        triage_result = await ai_triage_service.triage(title, description)
        agents_used.append("ai_triage")
        results["triage"] = {
            "priority": triage_result.priority,
            "category": triage_result.category,
            "confidence": triage_result.confidence,
            "reasoning": triage_result.reasoning,
        }
        confidences.append(triage_result.confidence)

        # MODERATE以上は修復候補分析も実行
        if complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX):
            repair_analysis = await auto_repair_service.analyze(incident_id, title, description)
            agents_used.append("auto_repair")
            results["repair_analysis"] = {
                "symptoms": repair_analysis.symptoms,
                "root_cause_hypothesis": repair_analysis.root_cause_hypothesis,
                "candidates_count": len(repair_analysis.candidates),
                "recommended_action": repair_analysis.recommended.action
                if repair_analysis.recommended
                else None,
            }
            if repair_analysis.recommended:
                confidences.append(repair_analysis.recommended.confidence)

        # COMPLEXは自動実行候補リストも抽出
        if complexity == TaskComplexity.COMPLEX:
            agents_used.append("auto_repair_executor")
            automated_candidates = [
                {"action": c.action, "risk_level": c.risk_level, "description": c.description}
                for c in (repair_analysis.candidates if "repair_analysis" in results else [])  # type: ignore[possibly-undefined]
                if c.automated and c.risk_level == "low"
            ]
            results["auto_executable"] = automated_candidates

        total_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        logger.info(
            "Agent orchestration complete",
            incident_id=incident_id,
            complexity=complexity,
            agents_used=agents_used,
            total_confidence=total_confidence,
        )

        return AgentTeamResult(
            task_id=incident_id,
            complexity=complexity,
            agents_used=agents_used,
            results=results,
            total_confidence=total_confidence,
        )


orchestrator = AgentOrchestrator()
