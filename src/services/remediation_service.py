"""AI自動リメディエーションサービス"""

import json
from datetime import UTC, datetime

import structlog

from src.models.remediation import (
    RemediationActionType,
    RemediationLog,
    RemediationRule,
    RemediationStatus,
)

logger = structlog.get_logger(__name__)


class RemediationEngine:
    """リメディエーション実行エンジン"""

    # アクションシミュレーター（実環境では実際の実行ロジックに差し替え）
    _ACTION_HANDLERS: dict[str, str] = {
        RemediationActionType.RESTART_SERVICE: "サービス再起動を実行しました",
        RemediationActionType.SCALE_UP: "スケールアップを実行しました",
        RemediationActionType.SCALE_DOWN: "スケールダウンを実行しました",
        RemediationActionType.FAILOVER: "フェイルオーバーを実行しました",
        RemediationActionType.CLEAR_CACHE: "キャッシュクリアを実行しました",
        RemediationActionType.ROLLBACK_DEPLOYMENT: "デプロイロールバックを実行しました",
        RemediationActionType.NOTIFY_ONCALL: "オンコール担当者に通知しました",
        RemediationActionType.RUN_PLAYBOOK: "プレイブックを実行しました",
        RemediationActionType.CUSTOM: "カスタムアクションを実行しました",
    }

    def execute_action(
        self,
        action_type: str,
        params: dict,
        dry_run: bool = False,
    ) -> tuple[bool, str]:
        """アクションを実行（dry_run=Trueの場合はシミュレーションのみ）"""
        handler_msg = self._ACTION_HANDLERS.get(action_type, f"不明なアクション: {action_type}")
        params_str = json.dumps(params, ensure_ascii=False)
        if dry_run:
            return True, f"[DRY-RUN] {handler_msg} (params={params_str})"
        logger.info("remediation_action_executed", action=action_type, params=params)
        return True, f"{handler_msg} (params={params_str})"


class RemediationService:
    """リメディエーション管理サービス"""

    def __init__(self) -> None:
        self._engine = RemediationEngine()

    # ── ルール管理 ──────────────────────────────────────────────────────────────

    def create_rule(self, session, rule_data: dict) -> RemediationRule:
        """リメディエーションルールを作成"""
        rule = RemediationRule(**rule_data)
        session.add(rule)
        return rule

    async def get_rules(self, session, enabled_only: bool = True) -> list[RemediationRule]:
        """ルール一覧取得（priority_order昇順）"""
        from sqlalchemy import select

        stmt = select(RemediationRule).order_by(RemediationRule.priority_order)
        if enabled_only:
            stmt = stmt.where(RemediationRule.is_enabled.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_rule(self, session, rule_id) -> RemediationRule | None:
        """ルール単件取得"""
        from sqlalchemy import select

        result = await session.execute(
            select(RemediationRule).where(RemediationRule.rule_id == rule_id)
        )
        return result.scalar_one_or_none()

    def update_rule(self, rule: RemediationRule, updates: dict) -> RemediationRule:
        """ルール更新"""
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        return rule

    # ── ルールマッチング ────────────────────────────────────────────────────────

    def match_rules(
        self,
        rules: list[RemediationRule],
        incident_data: dict,
        anomaly_score: float = 0.0,
    ) -> list[tuple[RemediationRule, float]]:
        """インシデントにマッチするルールを返す（信頼度スコア付き）"""
        matched = []
        for rule in rules:
            confidence = self._calculate_confidence(rule, incident_data, anomaly_score)
            if confidence >= rule.confidence_threshold:
                matched.append((rule, confidence))
        # 信頼度スコアの降順でソート
        matched.sort(key=lambda x: x[1], reverse=True)
        return matched

    def _calculate_confidence(
        self,
        rule: RemediationRule,
        incident_data: dict,
        anomaly_score: float,
    ) -> float:
        """ルールとインシデントの適合度（信頼度）を計算"""
        score = 0.0
        checks = 0

        if rule.match_priority:
            checks += 1
            if incident_data.get("priority") == rule.match_priority:
                score += 1.0

        if rule.match_status:
            checks += 1
            if incident_data.get("status") == rule.match_status:
                score += 1.0

        if rule.match_keyword:
            checks += 1
            title = incident_data.get("title", "").lower()
            if rule.match_keyword.lower() in title:
                score += 1.0

        if rule.min_anomaly_score > 0:
            checks += 1
            if anomaly_score >= rule.min_anomaly_score:
                score += 1.0

        # チェック条件がない場合は基本信頼度0.5
        if checks == 0:
            return 0.5
        return score / checks

    # ── リメディエーション実行 ───────────────────────────────────────────────────

    async def run_remediation(
        self,
        session,
        incident_id,
        rule: RemediationRule,
        confidence: float,
        dry_run: bool = False,
    ) -> RemediationLog:
        """リメディエーションを実行してログを記録"""
        params = {}
        if rule.action_params:
            try:
                params = json.loads(rule.action_params)
            except json.JSONDecodeError:
                params = {}

        # 承認フロー判定
        status = RemediationStatus.PENDING
        if rule.requires_approval and not dry_run:
            status = RemediationStatus.AWAITING_APPROVAL

        log = RemediationLog(
            incident_id=incident_id,
            rule_id=rule.rule_id,
            action_type=rule.action_type,
            action_params=json.dumps(params),
            status=status,
            is_dry_run=dry_run,
            confidence_score=confidence,
            started_at=datetime.now(UTC),
        )
        session.add(log)
        await session.flush()

        if status == RemediationStatus.AWAITING_APPROVAL:
            logger.info(
                "remediation_awaiting_approval",
                log_id=str(log.log_id),
                rule=rule.name,
            )
            return log

        # 実行
        start_ms = datetime.now(UTC)
        success, message = self._engine.execute_action(rule.action_type, params, dry_run)
        elapsed = int((datetime.now(UTC) - start_ms).total_seconds() * 1000)

        log.status = (
            RemediationStatus.DRY_RUN
            if dry_run
            else (RemediationStatus.SUCCESS if success else RemediationStatus.FAILED)
        )
        log.result_message = message
        log.completed_at = datetime.now(UTC)
        log.duration_ms = elapsed

        logger.info(
            "remediation_completed",
            log_id=str(log.log_id),
            status=log.status,
            dry_run=dry_run,
        )
        return log

    # ── ログ照会 ───────────────────────────────────────────────────────────────

    async def get_logs(
        self,
        session,
        incident_id=None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RemediationLog]:
        """リメディエーションログ一覧取得"""
        from sqlalchemy import select

        stmt = (
            select(RemediationLog)
            .order_by(RemediationLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if incident_id:
            stmt = stmt.where(RemediationLog.incident_id == incident_id)
        if status:
            stmt = stmt.where(RemediationLog.status == status)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_log(self, session, log_id) -> RemediationLog | None:
        """ログ単件取得"""
        from sqlalchemy import select

        result = await session.execute(
            select(RemediationLog).where(RemediationLog.log_id == log_id)
        )
        return result.scalar_one_or_none()

    async def approve_remediation(
        self, session, log: RemediationLog, approver: str
    ) -> RemediationLog:
        """保留中のリメディエーションを承認して実行"""
        if log.status != RemediationStatus.AWAITING_APPROVAL:
            raise ValueError(f"ログ {log.log_id} は承認待ち状態ではありません")

        log.approved_by = approver
        params = {}
        if log.action_params:
            try:
                params = json.loads(log.action_params)
            except json.JSONDecodeError:
                params = {}

        success, message = self._engine.execute_action(log.action_type, params, False)
        log.status = RemediationStatus.SUCCESS if success else RemediationStatus.FAILED
        log.result_message = message
        log.completed_at = datetime.now(UTC)
        return log
