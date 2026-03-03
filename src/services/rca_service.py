"""根本原因分析（RCA）サービス - パターンマッチング + 類似インシデント検索"""

import uuid
from dataclasses import dataclass, field

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cmdb import ConfigurationItem
from src.models.incident import Incident
from src.models.problem import Problem

logger = structlog.get_logger()


@dataclass
class RCACandidate:
    """根本原因候補"""

    cause_category: str  # Infrastructure/Application/Network/Database/Security/Human_Error/Unknown
    description: str
    confidence: float  # 0.0-1.0
    evidence: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


@dataclass
class RCAResult:
    """RCA分析結果"""

    problem_id: str
    candidates: list[RCACandidate] = field(default_factory=list)
    similar_incidents: list[str] = field(default_factory=list)
    affected_cis: list[str] = field(default_factory=list)
    analysis_summary: str = ""


class RCAService:
    """根本原因分析サービス"""

    INFRA_PATTERNS = ["server", "cpu", "memory", "disk", "hardware", "サーバー", "メモリ"]
    APP_PATTERNS = ["application", "service", "api", "deploy", "release", "アプリ", "デプロイ"]
    NETWORK_PATTERNS = ["network", "timeout", "connection", "dns", "ネットワーク", "接続"]
    DB_PATTERNS = ["database", "db", "query", "deadlock", "データベース", "クエリ"]
    SECURITY_PATTERNS = ["security", "unauthorized", "breach", "attack", "セキュリティ", "不正"]
    HUMAN_PATTERNS = ["misconfiguration", "config", "human", "manual", "設定ミス", "誤操作"]

    _CATEGORY_PATTERNS: dict[str, list[str]] = {}

    def __post_init__(self) -> None:  # pragma: no cover
        pass

    def _build_category_patterns(self) -> dict[str, list[str]]:
        return {
            "Infrastructure": self.INFRA_PATTERNS,
            "Application": self.APP_PATTERNS,
            "Network": self.NETWORK_PATTERNS,
            "Database": self.DB_PATTERNS,
            "Security": self.SECURITY_PATTERNS,
            "Human_Error": self.HUMAN_PATTERNS,
        }

    async def analyze_problem(self, db: AsyncSession, problem_id: str) -> RCAResult:
        """Problemに紐づくIncident群からRCAを実行"""
        # 1. Problemを取得
        uid = uuid.UUID(problem_id) if isinstance(problem_id, str) else problem_id
        result = await db.execute(select(Problem).where(Problem.problem_id == uid))
        problem = result.scalar_one_or_none()

        if not problem:
            logger.warning("rca_problem_not_found", problem_id=problem_id)
            return RCAResult(
                problem_id=problem_id,
                analysis_summary="対象のProblemが見つかりませんでした。",
            )

        # 2. 分析テキストを構築
        text_parts = [problem.title or ""]
        if problem.description:
            text_parts.append(problem.description)
        if problem.root_cause:
            text_parts.append(problem.root_cause)
        analysis_text = " ".join(text_parts)

        # 3. 類似インシデントを検索
        similar = await self.find_similar_incidents(db, problem.title)
        similar_numbers = [inc.incident_number for inc in similar]

        # 4. 影響CIをCMDBから取得
        affected_cis = await self._find_affected_cis(db, analysis_text)

        # 5. RCA候補を生成
        category, confidence = self._categorize_cause(analysis_text)
        recommendations = self._generate_recommendations(category)
        evidence = similar_numbers[:3]

        candidate = RCACandidate(
            cause_category=category,
            description=f"{category}カテゴリに関連する根本原因が検出されました。",
            confidence=confidence,
            evidence=evidence,
            recommended_actions=recommendations,
        )

        summary = (
            f"RCA分析完了: 1件の候補を特定。主要カテゴリ: {category}"
            f"（信頼度: {confidence:.2f}）。類似インシデント{len(similar_numbers)}件を参照。"
        )

        logger.info(
            "rca_analysis_completed",
            problem_id=problem_id,
            category=category,
            confidence=confidence,
            similar_count=len(similar_numbers),
        )

        return RCAResult(
            problem_id=problem_id,
            candidates=[candidate],
            similar_incidents=similar_numbers,
            affected_cis=affected_cis,
            analysis_summary=summary,
        )

    async def find_similar_incidents(
        self, db: AsyncSession, title: str, limit: int = 5
    ) -> list[Incident]:
        """類似インシデントを検索（タイトルキーワードマッチング）"""
        keywords = [w for w in title.split() if len(w) >= 3]
        if not keywords:
            return []

        conditions = [Incident.title.ilike(f"%{kw}%") for kw in keywords]
        query = select(Incident).where(or_(*conditions)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def _find_affected_cis(self, db: AsyncSession, text: str) -> list[str]:
        """テキストに含まれるキーワードにマッチするCIを検索"""
        keywords = [w for w in text.split() if len(w) >= 4]
        if not keywords:
            return []

        conditions = [ConfigurationItem.ci_name.ilike(f"%{kw}%") for kw in keywords[:5]]
        query = select(ConfigurationItem.ci_name).where(or_(*conditions)).limit(10)
        result = await db.execute(query)
        return list(result.scalars().all())

    def _categorize_cause(self, text: str) -> tuple[str, float]:
        """テキストからカテゴリと信頼度を判定"""
        text_lower = text.lower()
        patterns = self._build_category_patterns()
        scores: dict[str, int] = {
            cat: sum(1 for p in pats if p.lower() in text_lower) for cat, pats in patterns.items()
        }

        best_category = max(scores, key=lambda k: scores[k])
        best_score = scores[best_category]

        if best_score == 0:
            return "Unknown", 0.0

        total = sum(scores.values())
        confidence = round(best_score / total, 2) if total > 0 else 0.0
        return best_category, confidence

    def _generate_recommendations(self, category: str) -> list[str]:
        """カテゴリに応じた推奨アクションを返す"""
        recommendations = {
            "Infrastructure": [
                "インフラリソース使用率の監視強化",
                "キャパシティプランニングの見直し",
                "冗長化・フェイルオーバー検討",
            ],
            "Application": [
                "デプロイプロセスの見直し",
                "ロールバック手順の整備",
                "ステージング環境でのテスト強化",
            ],
            "Network": [
                "ネットワーク経路の冗長化",
                "DDOSプロテクションの検討",
                "DNS/CDN設定の見直し",
            ],
            "Database": [
                "クエリ最適化・インデックス見直し",
                "DB接続プールの調整",
                "バックアップ・リカバリ手順確認",
            ],
            "Security": [
                "セキュリティパッチ適用",
                "アクセスログ監査",
                "インシデントレスポンス手順見直し",
            ],
            "Human_Error": [
                "変更管理プロセス強化",
                "作業前チェックリスト整備",
                "ロールバック手順の明確化",
            ],
        }
        return recommendations.get(category, ["根本原因の詳細調査", "予防措置の検討"])


rca_service = RCAService()
