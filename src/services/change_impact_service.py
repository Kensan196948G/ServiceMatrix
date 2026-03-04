"""変更影響分析サービス - RFC自動リスク評価・影響CI特定・競合チェック"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.change import Change
from src.models.cmdb import ConfigurationItem
from src.services.ai_decision_log_service import AIDecision, ai_decision_log_service

logger = get_logger(__name__)

MAX_AFFECTED_CIS = 5
MAX_CONFLICTING_CHANGES = 5
CONFLICT_WINDOW_DAYS = 3


@dataclass
class ChangeImpactResult:
    change_id: str
    risk_level: str           # "Critical"/"High"/"Medium"/"Low"
    risk_score: float         # 0.0-1.0
    affected_cis: list[dict]  # [{"ci_id": str, "name": str, "ci_type": str}]
    conflicting_changes: list[dict]  # [{"change_id": str, "title": str, "scheduled_date": str}]
    recommendations: list[str]
    analysis_reasoning: str


class ChangeImpactService:
    """RFC変更影響自動分析エンジン"""

    async def analyze_impact(self, db: AsyncSession, change_id: str) -> ChangeImpactResult:
        """変更のリスク評価・影響CI特定・競合チェックを実行"""
        import uuid as _uuid
        result = await db.execute(select(Change).where(Change.change_id == _uuid.UUID(change_id)))
        change = result.scalar_one_or_none()
        if change is None:
            raise ValueError(f"Change not found: {change_id}")

        # risk_score (0.0-1.0) および risk_level を決定
        raw_score = change.risk_score if change.risk_score else None
        if raw_score:
            risk_score = min(raw_score / 100.0, 1.0)
        else:
            risk_score = 0.5
        risk_level = self._score_to_level(risk_score)

        affected_cis = await self._find_affected_cis(db, change.title)
        conflicting_changes = await self._find_conflicting_changes(db, change)
        recommendations = self._build_recommendations(
            risk_level, affected_cis, conflicting_changes, change
        )
        reasoning = self._build_reasoning(risk_level, risk_score, affected_cis, conflicting_changes)

        impact = ChangeImpactResult(
            change_id=change_id,
            risk_level=risk_level,
            risk_score=risk_score,
            affected_cis=affected_cis,
            conflicting_changes=conflicting_changes,
            recommendations=recommendations,
            analysis_reasoning=reasoning,
        )

        await ai_decision_log_service.record(
            AIDecision(
                action="change_impact",
                entity_type="change",
                entity_id=change_id,
                input_data={"change_id": change_id, "title": change.title},
                output_data={
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "affected_cis_count": len(affected_cis),
                    "conflicting_changes_count": len(conflicting_changes),
                },
                confidence=risk_score,
                provider="rule_based",
            )
        )

        logger.info(
            "change_impact_analyzed",
            change_id=change_id,
            risk_level=risk_level,
            risk_score=risk_score,
            affected_cis=len(affected_cis),
            conflicting_changes=len(conflicting_changes),
        )

        return impact

    def _score_to_level(self, risk_score: float) -> str:
        if risk_score >= 0.8:
            return "Critical"
        elif risk_score >= 0.6:
            return "High"
        elif risk_score >= 0.4:
            return "Medium"
        return "Low"

    async def _find_affected_cis(self, db: AsyncSession, title: str) -> list[dict]:
        """変更タイトルのキーワードでCIを検索（最大5件）"""
        keywords = [w for w in title.split() if len(w) >= 3][:5]
        if not keywords:
            return []

        conditions = [ConfigurationItem.ci_name.ilike(f"%{kw}%") for kw in keywords]
        q = (
            select(ConfigurationItem)
            .where(or_(*conditions))
            .limit(MAX_AFFECTED_CIS)
        )
        rows = await db.execute(q)
        cis = rows.scalars().all()
        return [
            {"ci_id": str(ci.ci_id), "name": ci.ci_name, "ci_type": ci.ci_type}
            for ci in cis
        ]

    async def _find_conflicting_changes(self, db: AsyncSession, change: Change) -> list[dict]:
        """±3日以内に予定されている他のChange（最大5件）"""
        anchor: datetime = change.scheduled_start_at or change.created_at
        window_start = anchor - timedelta(days=CONFLICT_WINDOW_DAYS)
        window_end = anchor + timedelta(days=CONFLICT_WINDOW_DAYS)

        date_col = Change.scheduled_start_at if change.scheduled_start_at else Change.created_at

        q = (
            select(Change)
            .where(
                Change.change_id != change.change_id,
                date_col >= window_start,
                date_col <= window_end,
            )
            .limit(MAX_CONFLICTING_CHANGES)
        )
        rows = await db.execute(q)
        others = rows.scalars().all()

        return [
            {
                "change_id": str(c.change_id),
                "title": c.title,
                "scheduled_date": (
                    c.scheduled_start_at.isoformat()
                    if c.scheduled_start_at
                    else c.created_at.isoformat()
                ),
            }
            for c in others
        ]

    def _build_recommendations(
        self,
        risk_level: str,
        affected_cis: list[dict],
        conflicting_changes: list[dict],
        change: Change,
    ) -> list[str]:
        recs: list[str] = []
        if risk_level in ("High", "Critical"):
            recs.append("変更諮問委員会（CAB）への緊急レビューを依頼してください")
        if conflicting_changes:
            recs.append(
                f"同期間に{len(conflicting_changes)}件の競合変更があります。調整を推奨します"
            )
        if affected_cis:
            recs.append(
                f"{len(affected_cis)}件の影響CIが特定されました。各CIオーナーへの通知を推奨します"
            )
        if not change.rollback_plan:
            recs.append("ロールバック計画を作成してください")
        if not change.test_plan:
            recs.append("テスト計画を追加してください")
        if risk_level == "Critical":
            recs.append("メンテナンスウィンドウでの実施を強く推奨します")
        return recs

    def _build_reasoning(
        self,
        risk_level: str,
        risk_score: float,
        affected_cis: list[dict],
        conflicting_changes: list[dict],
    ) -> str:
        parts = [
            f"リスクスコア {risk_score:.2f} に基づきリスクレベル '{risk_level}' と判定。",
            f"影響CI: {len(affected_cis)}件。" if affected_cis else "影響CIなし。",
            f"競合変更: {len(conflicting_changes)}件検出。" if conflicting_changes else "競合変更なし。",
        ]
        return " ".join(parts)


change_impact_service = ChangeImpactService()
