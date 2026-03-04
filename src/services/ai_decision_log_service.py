"""AI決定ログサービス - 全AI判断の記録・監査証跡"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIDecision:
    action: str  # "triage", "rca", "change_risk", "similar_search"
    entity_type: str  # "incident", "change", "problem"
    entity_id: str
    input_data: dict
    output_data: dict
    confidence: float
    provider: str  # "keyword", "openai", "rule_based"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class AIDecisionLogService:
    """AI判断の全記録（インメモリ + ログ出力）"""

    def __init__(self) -> None:
        self._decisions: list[AIDecision] = []

    async def record(self, decision: AIDecision) -> None:
        self._decisions.append(decision)
        logger.info(
            "AI decision recorded",
            action=decision.action,
            entity_type=decision.entity_type,
            entity_id=decision.entity_id,
            confidence=decision.confidence,
            provider=decision.provider,
        )

    async def get_decisions(
        self, entity_id: str | None = None, action: str | None = None
    ) -> list[AIDecision]:
        results = self._decisions
        if entity_id is not None:
            results = [d for d in results if d.entity_id == entity_id]
        if action is not None:
            results = [d for d in results if d.action == action]
        return list(results)

    async def get_summary(self) -> dict:
        total = len(self._decisions)
        by_action: dict[str, int] = {}
        by_provider: dict[str, int] = {}
        confidence_sum = 0.0
        for d in self._decisions:
            by_action[d.action] = by_action.get(d.action, 0) + 1
            by_provider[d.provider] = by_provider.get(d.provider, 0) + 1
            confidence_sum += d.confidence
        return {
            "total": total,
            "by_action": by_action,
            "by_provider": by_provider,
            "avg_confidence": round(confidence_sum / total, 4) if total > 0 else 0.0,
        }


ai_decision_log_service = AIDecisionLogService()
