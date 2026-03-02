"""Change管理リスク自動評価サービス"""
import uuid as _uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.change import Change

logger = structlog.get_logger()


@dataclass
class RiskFactor:
    """リスク要因"""

    factor_name: str
    score: int  # 0-25（各要因の最大スコア）
    description: str


@dataclass
class RiskAssessmentResult:
    """リスク評価結果"""

    change_id: str
    total_score: int  # 0-100
    risk_level: str  # Low/Medium/High/Critical
    factors: list[RiskFactor]
    recommendations: list[str]
    maintenance_window_required: bool  # 深夜・週末作業推奨フラグ


class ChangeRiskService:
    """Change管理リスク自動評価サービス"""

    RISK_THRESHOLDS = {"Low": 25, "Medium": 50, "High": 75, "Critical": 100}

    CHANGE_TYPE_SCORES = {
        "Emergency": 25,
        "Normal": 10,
        "Standard": 5,
        "Major": 15,
    }

    async def assess_risk(self, db: AsyncSession, change_id: str) -> RiskAssessmentResult:
        """Changeのリスクを自動評価"""
        result = await db.execute(
            select(Change).where(Change.change_id == _uuid.UUID(change_id))
        )
        change = result.scalar_one_or_none()
        if change is None:
            raise ValueError(f"Change not found: {change_id}")

        # 各リスク要因を評価
        type_factor = self._score_change_type(change.change_type)
        timing_factor = self._score_change_timing(change.scheduled_start_at)
        history_factor = await self._score_historical_failure(db, change.change_type)
        detail_factor = self._score_description_detail(change.description, change.test_plan)

        factors = [type_factor, timing_factor, history_factor, detail_factor]
        total_score = min(sum(f.score for f in factors), 100)
        risk_level = self._determine_risk_level(total_score)
        recommendations = self._generate_recommendations(factors, risk_level)
        maintenance_window_required = timing_factor.score > 0 or risk_level in ("High", "Critical")

        # Changeモデルを更新
        change.risk_score = total_score
        change.risk_level = risk_level
        await db.flush()

        logger.info(
            "change_risk_assessed",
            change_id=change_id,
            total_score=total_score,
            risk_level=risk_level,
        )

        return RiskAssessmentResult(
            change_id=change_id,
            total_score=total_score,
            risk_level=risk_level,
            factors=factors,
            recommendations=recommendations,
            maintenance_window_required=maintenance_window_required,
        )

    def _score_change_type(self, change_type: str) -> RiskFactor:
        """変更種別のリスクスコア"""
        score = self.CHANGE_TYPE_SCORES.get(change_type, 10)
        return RiskFactor("change_type", score, f"変更種別: {change_type}")

    def _score_change_timing(self, scheduled_start: datetime | None) -> RiskFactor:
        """変更時間帯のリスクスコア"""
        if scheduled_start is None:
            return RiskFactor("timing", 5, "実施予定日時未設定")

        hour = scheduled_start.hour
        weekday = scheduled_start.weekday()  # 0=月曜, 5=土曜, 6=日曜

        if weekday >= 5:  # 週末
            return RiskFactor("timing", 20, f"週末作業 ({scheduled_start.strftime('%Y-%m-%d')})")
        elif hour < 7 or hour >= 20:  # 深夜・早朝
            return RiskFactor("timing", 15, f"時間外作業 ({hour:02d}:00)")
        else:
            return RiskFactor("timing", 0, "営業時間内作業")

    async def _score_historical_failure(
        self, db: AsyncSession, change_type: str
    ) -> RiskFactor:
        """過去の失敗率スコア（直近30日のFailed件数×3、上限25）"""
        since = datetime.now(UTC) - timedelta(days=30)
        result = await db.execute(
            select(func.count()).where(
                Change.status == "Failed",
                Change.change_type == change_type,
                Change.created_at >= since,
            )
        )
        failure_count = result.scalar_one()
        score = min(failure_count * 3, 25)
        return RiskFactor(
            "historical_failure",
            score,
            f"直近30日の同種別失敗件数: {failure_count}件",
        )

    def _score_description_detail(
        self, description: str | None, test_plan: str | None
    ) -> RiskFactor:
        """説明の詳細度スコア"""
        score = 0
        reasons = []
        if not description or len(description) < 50:
            score += 10
            reasons.append("変更内容の説明が不十分 (<50文字)")
        if not test_plan:
            score += 5
            reasons.append("テスト計画未設定")
        description_text = "、".join(reasons) if reasons else "説明・テスト計画あり"
        return RiskFactor("description_detail", score, description_text)

    def _determine_risk_level(self, score: int) -> str:
        if score <= 25:
            return "Low"
        elif score <= 50:
            return "Medium"
        elif score <= 75:
            return "High"
        else:
            return "Critical"

    def _generate_recommendations(
        self, factors: list[RiskFactor], risk_level: str
    ) -> list[str]:
        recommendations: list[str] = []
        factor_map = {f.factor_name: f for f in factors}

        if factor_map.get("change_type", RiskFactor("", 0, "")).score >= 25:
            recommendations.append("緊急変更のため、承認者への事前連絡を推奨します")

        timing = factor_map.get("timing", RiskFactor("", 0, ""))
        if timing.score > 0:
            recommendations.append("メンテナンスウィンドウ（深夜・週末）での実施を推奨します")

        history = factor_map.get("historical_failure", RiskFactor("", 0, ""))
        if history.score >= 9:
            recommendations.append("過去の失敗率が高いため、ロールバック計画を再確認してください")

        detail = factor_map.get("description_detail", RiskFactor("", 0, ""))
        if "テスト計画未設定" in detail.description:
            recommendations.append("テスト計画を追加してください")
        if "説明が不十分" in detail.description:
            recommendations.append("変更内容の詳細な記述を推奨します")

        if risk_level in ("High", "Critical"):
            recommendations.append("変更諮問委員会（CAB）への緊急レビューを依頼してください")

        return recommendations


change_risk_service = ChangeRiskService()
