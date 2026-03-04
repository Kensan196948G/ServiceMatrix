"""自動修復Agentサービス - CI失敗診断・修復候補生成"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.logging import get_logger
from src.services.ai_decision_log_service import AIDecision, ai_decision_log_service

logger = get_logger(__name__)


@dataclass
class RepairCandidate:
    action: str  # "restart_service", "clear_cache", "rollback", "scale_up", "manual"
    description: str
    risk_level: str  # "low", "medium", "high"
    confidence: float  # 0.0-1.0
    automated: bool  # True=自動実行可能
    steps: list[str] = field(default_factory=list)


@dataclass
class RepairAnalysis:
    incident_id: str
    symptoms: list[str]
    root_cause_hypothesis: str
    candidates: list[RepairCandidate]
    recommended: RepairCandidate | None
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AutoRepairService:
    """AI自動修復候補生成エンジン"""

    # 症状→修復アクションルールベース
    REPAIR_RULES: dict[str, list[RepairCandidate]] = {
        "timeout": [
            RepairCandidate(
                "clear_cache",
                "キャッシュクリアを実行",
                "low",
                0.8,
                True,
                ["1. アプリケーションキャッシュクリア", "2. 再起動"],
            ),
            RepairCandidate(
                "scale_up",
                "リソーススケールアップ",
                "medium",
                0.7,
                False,
                ["1. CPU/メモリ使用率確認", "2. スケールアップ実行"],
            ),
        ],
        "error": [
            RepairCandidate(
                "rollback",
                "直前バージョンへロールバック",
                "medium",
                0.75,
                False,
                ["1. 直前デプロイメント特定", "2. ロールバック実行", "3. 動作確認"],
            ),
            RepairCandidate(
                "restart_service",
                "サービス再起動",
                "low",
                0.85,
                True,
                ["1. サービス停止", "2. 30秒待機", "3. サービス起動"],
            ),
        ],
        "outage": [
            RepairCandidate(
                "restart_service",
                "緊急サービス再起動",
                "medium",
                0.9,
                True,
                ["1. 影響範囲特定", "2. サービス再起動", "3. 監視強化"],
            ),
            RepairCandidate(
                "rollback",
                "緊急ロールバック",
                "high",
                0.8,
                False,
                ["1. 変更履歴確認", "2. 承認後ロールバック"],
            ),
        ],
        "performance": [
            RepairCandidate(
                "clear_cache",
                "キャッシュ最適化",
                "low",
                0.7,
                True,
                ["1. キャッシュヒット率確認", "2. キャッシュクリア"],
            ),
            RepairCandidate(
                "scale_up",
                "スケールアップ",
                "medium",
                0.75,
                False,
                ["1. ボトルネック特定", "2. リソース追加"],
            ),
        ],
    }

    # テキストから症状を抽出するキーワードマッピング
    _SYMPTOM_KEYWORDS: dict[str, list[str]] = {
        "timeout": ["timeout", "timed out", "タイムアウト", "応答なし", "hang"],
        "error": ["error", "failed", "failure", "exception", "エラー", "失敗", "障害"],
        "outage": ["outage", "down", "unavailable", "停止", "ダウン", "障害"],
        "performance": [
            "slow",
            "performance",
            "latency",
            "遅い",
            "遅延",
            "高負荷",
            "cpu",
            "memory",
        ],
    }

    async def analyze(
        self, incident_id: str, title: str, description: str | None
    ) -> RepairAnalysis:
        """インシデントを分析して修復候補を生成"""
        text = f"{title} {description or ''}".lower()
        symptoms = self._extract_symptoms(text)
        candidates = self._get_candidates(symptoms)
        recommended = self._select_best_candidate(candidates)
        root_cause = self._hypothesize_root_cause(symptoms, text)

        analysis = RepairAnalysis(
            incident_id=incident_id,
            symptoms=symptoms,
            root_cause_hypothesis=root_cause,
            candidates=candidates,
            recommended=recommended,
        )

        await ai_decision_log_service.record(
            AIDecision(
                action="auto_repair",
                entity_type="incident",
                entity_id=incident_id,
                input_data={"title": title, "symptoms": symptoms},
                output_data={
                    "candidates": len(candidates),
                    "recommended": recommended.action if recommended else None,
                },
                confidence=recommended.confidence if recommended else 0.0,
                provider="rule_based",
                timestamp=datetime.now(UTC),
            )
        )

        logger.info(
            "Auto repair analysis complete",
            incident_id=incident_id,
            symptoms=symptoms,
            candidates=len(candidates),
            recommended=recommended.action if recommended else None,
        )
        return analysis

    async def execute_low_risk(self, incident_id: str, title: str, description: str | None) -> dict:
        """低リスク修復の自動実行（シミュレーション）"""
        analysis = await self.analyze(incident_id, title, description)
        executed = []
        skipped = []

        for candidate in analysis.candidates:
            if candidate.automated and candidate.risk_level == "low":
                executed.append(
                    {
                        "action": candidate.action,
                        "description": candidate.description,
                        "steps": candidate.steps,
                        "simulated": True,
                    }
                )
                logger.info(
                    "Auto repair executed (simulation)",
                    incident_id=incident_id,
                    action=candidate.action,
                    risk_level=candidate.risk_level,
                )
            else:
                skipped.append(
                    {
                        "action": candidate.action,
                        "reason": "risk_level_not_low"
                        if candidate.risk_level != "low"
                        else "not_automated",
                    }
                )

        return {
            "incident_id": incident_id,
            "executed": executed,
            "skipped": skipped,
            "simulation": True,
        }

    def _extract_symptoms(self, text: str) -> list[str]:
        found: list[str] = []
        for symptom, keywords in self._SYMPTOM_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                found.append(symptom)
        return found

    def _get_candidates(self, symptoms: list[str]) -> list[RepairCandidate]:
        seen_actions: set[str] = set()
        candidates: list[RepairCandidate] = []
        for symptom in symptoms:
            for candidate in self.REPAIR_RULES.get(symptom, []):
                if candidate.action not in seen_actions:
                    seen_actions.add(candidate.action)
                    candidates.append(candidate)
        if not candidates:
            candidates.append(
                RepairCandidate(
                    "manual",
                    "手動調査が必要です",
                    "low",
                    0.5,
                    False,
                    ["1. ログ収集", "2. 担当者エスカレーション"],
                )
            )
        return candidates

    def _select_best_candidate(self, candidates: list[RepairCandidate]) -> RepairCandidate | None:
        if not candidates:
            return None
        # 最高信頼度の候補を選択（同率の場合はリスクが低い方を優先）
        risk_order = {"low": 0, "medium": 1, "high": 2}
        return max(
            candidates,
            key=lambda c: (c.confidence, -risk_order.get(c.risk_level, 1)),
        )

    def _hypothesize_root_cause(self, symptoms: list[str], text: str) -> str:
        if not symptoms:
            return "原因不明 - 追加調査が必要です"

        hypotheses: list[str] = []
        if "outage" in symptoms:
            hypotheses.append("サービス全体の停止（デプロイ失敗またはインフラ障害の可能性）")
        if "error" in symptoms:
            hypotheses.append("アプリケーションエラー（コード不具合またはデータ不整合の可能性）")
        if "timeout" in symptoms:
            hypotheses.append("応答タイムアウト（リソース不足またはデッドロックの可能性）")
        if "performance" in symptoms:
            hypotheses.append("パフォーマンス劣化（リソース枯渇またはクエリ最適化不足の可能性）")

        return " / ".join(hypotheses) if hypotheses else "複合的な要因による障害"


auto_repair_service = AutoRepairService()
