"""AIトリアージサービス - キーワードベース優先度・カテゴリ自動判定"""
import uuid as _uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.incident import Incident

logger = get_logger(__name__)


@dataclass
class AITriageResult:
    priority: str  # Critical/High/Medium/Low
    category: str  # Network/Database/Application/Security/Infrastructure/Unknown
    confidence: float  # 0.0-1.0
    reasoning: str


class AITriageService:
    """キーワードマッチングによるトリアージエンジン（本番ではLLM APIに差し替え可能）"""

    CRITICAL_KEYWORDS = ["down", "outage", "critical", "production", "障害", "停止", "緊急"]
    HIGH_KEYWORDS = ["error", "failed", "timeout", "エラー", "失敗", "遅延"]
    LOW_KEYWORDS = ["info", "inquiry", "question", "request", "情報", "問い合わせ", "確認"]

    SECURITY_KEYWORDS = ["security", "breach", "unauthorized", "exploit", "セキュリティ", "不正"]
    NETWORK_KEYWORDS = ["network", "connectivity", "dns", "firewall", "ネットワーク", "接続"]
    DB_KEYWORDS = ["database", "db", "sql", "query", "データベース", "クエリ"]
    INFRA_KEYWORDS = ["server", "cpu", "memory", "disk", "load", "サーバー", "メモリ", "ディスク"]

    async def triage(self, title: str, description: str | None) -> AITriageResult:
        """キーワードマッチングで優先度・カテゴリを判定する"""
        text = f"{title} {description or ''}".lower()

        priority, priority_confidence, priority_reason = self._determine_priority(text)
        category, category_reason = self._determine_category(text)

        reasoning = f"Priority: {priority_reason}. Category: {category_reason}."
        return AITriageResult(
            priority=priority,
            category=category,
            confidence=priority_confidence,
            reasoning=reasoning,
        )

    def _determine_priority(self, text: str) -> tuple[str, float, str]:
        if any(kw in text for kw in self.CRITICAL_KEYWORDS):
            matched = [kw for kw in self.CRITICAL_KEYWORDS if kw in text]
            return "Critical", 0.9, f"Critical keywords matched: {matched}"
        if any(kw in text for kw in self.HIGH_KEYWORDS):
            matched = [kw for kw in self.HIGH_KEYWORDS if kw in text]
            return "High", 0.8, f"High keywords matched: {matched}"
        if any(kw in text for kw in self.LOW_KEYWORDS):
            matched = [kw for kw in self.LOW_KEYWORDS if kw in text]
            return "Low", 0.7, f"Low keywords matched: {matched}"
        return "Medium", 0.5, "No priority keywords matched; defaulting to Medium"

    def _determine_category(self, text: str) -> tuple[str, str]:
        if any(kw in text for kw in self.SECURITY_KEYWORDS):
            matched = [kw for kw in self.SECURITY_KEYWORDS if kw in text]
            return "Security", f"Security keywords matched: {matched}"
        if any(kw in text for kw in self.NETWORK_KEYWORDS):
            matched = [kw for kw in self.NETWORK_KEYWORDS if kw in text]
            return "Network", f"Network keywords matched: {matched}"
        if any(kw in text for kw in self.DB_KEYWORDS):
            matched = [kw for kw in self.DB_KEYWORDS if kw in text]
            return "Database", f"Database keywords matched: {matched}"
        if any(kw in text for kw in self.INFRA_KEYWORDS):
            matched = [kw for kw in self.INFRA_KEYWORDS if kw in text]
            return "Infrastructure", f"Infrastructure keywords matched: {matched}"
        return "Unknown", "No category keywords matched"

    async def apply_triage_to_incident(
        self, db: AsyncSession, incident_id: str
    ) -> AITriageResult:
        """インシデントを取得してトリアージ実行・結果を保存する"""
        result = await db.execute(
            select(Incident).where(
                Incident.incident_id == _uuid.UUID(incident_id) if isinstance(incident_id, str)
                else incident_id
            )
        )
        incident = result.scalar_one_or_none()
        if not incident:
            logger.warning("Incident %s not found for triage", incident_id)
            return AITriageResult(
                priority="Unknown",
                category="Unknown",
                confidence=0.0,
                reasoning="Incident not found",
            )

        triage_result = await self.triage(incident.title, incident.description)
        incident.ai_triage_notes = (
            f"[AI Triage] Priority={triage_result.priority} "
            f"Category={triage_result.category} "
            f"Confidence={triage_result.confidence:.2f}\n"
            f"{triage_result.reasoning}"
        )
        await db.flush()
        logger.info(
            "Triage applied to incident %s: %s/%s",
            incident_id,
            triage_result.priority,
            triage_result.category,
        )
        return triage_result


ai_triage_service = AITriageService()
