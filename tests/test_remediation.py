"""AI自動リメディエーション テストスイート"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.remediation import (
    RemediationActionType,
    RemediationLog,
    RemediationRule,
    RemediationStatus,
)
from src.services.remediation_service import RemediationEngine, RemediationService

# ── フィクスチャ ───────────────────────────────────────────────────────────────


def make_rule(**kwargs) -> RemediationRule:
    defaults = {
        "rule_id": uuid.uuid4(),
        "name": "test_rule",
        "description": "テスト用ルール",
        "match_priority": "P1",
        "match_status": None,
        "match_keyword": None,
        "min_anomaly_score": 0.0,
        "action_type": RemediationActionType.RESTART_SERVICE,
        "action_params": None,
        "playbook_path": None,
        "requires_approval": False,
        "confidence_threshold": 0.7,
        "max_executions_per_hour": 3,
        "is_enabled": True,
        "priority_order": 100,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    rule = MagicMock(spec=RemediationRule)
    for k, v in defaults.items():
        setattr(rule, k, v)
    return rule


def make_log(**kwargs) -> RemediationLog:
    defaults = {
        "log_id": uuid.uuid4(),
        "incident_id": uuid.uuid4(),
        "rule_id": uuid.uuid4(),
        "action_type": RemediationActionType.RESTART_SERVICE,
        "action_params": None,
        "status": RemediationStatus.PENDING,
        "is_dry_run": False,
        "confidence_score": 0.9,
        "result_message": None,
        "error_message": None,
        "duration_ms": None,
        "approved_by": None,
        "started_at": None,
        "completed_at": None,
        "rollback_log_id": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    log = MagicMock(spec=RemediationLog)
    for k, v in defaults.items():
        setattr(log, k, v)
    return log


# ── RemediationEngine テスト ───────────────────────────────────────────────────


class TestRemediationEngine:
    def test_execute_action_success(self):
        engine = RemediationEngine()
        ok, msg = engine.execute_action(RemediationActionType.RESTART_SERVICE, {})
        assert ok is True
        assert "再起動" in msg

    def test_execute_action_dry_run(self):
        engine = RemediationEngine()
        ok, msg = engine.execute_action(
            RemediationActionType.SCALE_UP, {"target": "web"}, dry_run=True
        )
        assert ok is True
        assert "[DRY-RUN]" in msg
        assert "web" in msg

    def test_execute_action_all_types(self):
        engine = RemediationEngine()
        for action in RemediationActionType:
            ok, msg = engine.execute_action(action, {})
            assert ok is True
            assert isinstance(msg, str)

    def test_execute_unknown_action(self):
        engine = RemediationEngine()
        ok, msg = engine.execute_action("unknown_action", {})
        assert ok is True
        assert "unknown_action" in msg


# ── RemediationService ルールマッチング テスト ────────────────────────────────


class TestRuleMatching:
    def setup_method(self):
        self.svc = RemediationService()

    def test_match_by_priority(self):
        rule = make_rule(match_priority="P1", confidence_threshold=0.7)
        incident = {"priority": "P1", "status": "New", "title": "テスト"}
        matched = self.svc.match_rules([rule], incident, 0.0)
        assert len(matched) == 1
        assert matched[0][0] is rule

    def test_no_match_wrong_priority(self):
        rule = make_rule(match_priority="P1", confidence_threshold=0.7)
        incident = {"priority": "P4", "status": "New", "title": "テスト"}
        matched = self.svc.match_rules([rule], incident, 0.0)
        assert len(matched) == 0

    def test_match_by_keyword(self):
        rule = make_rule(
            match_priority=None,
            match_keyword="データベース",
            confidence_threshold=0.7,
        )
        incident = {"priority": "P2", "status": "New", "title": "データベース接続エラー"}
        matched = self.svc.match_rules([rule], incident, 0.0)
        assert len(matched) == 1

    def test_match_by_anomaly_score(self):
        rule = make_rule(
            match_priority=None,
            min_anomaly_score=0.8,
            confidence_threshold=0.7,
        )
        incident = {"priority": "P3", "status": "New", "title": "テスト"}
        matched = self.svc.match_rules([rule], incident, anomaly_score=0.9)
        assert len(matched) == 1

    def test_match_multiple_conditions(self):
        rule = make_rule(
            match_priority="P1",
            match_keyword="CPU",
            confidence_threshold=0.5,
        )
        incident = {"priority": "P1", "status": "New", "title": "CPU使用率異常"}
        matched = self.svc.match_rules([rule], incident, 0.0)
        assert len(matched) == 1
        # 2/2 = 1.0 の信頼度
        assert matched[0][1] == 1.0

    def test_no_conditions_returns_base_confidence(self):
        rule = make_rule(
            match_priority=None,
            match_status=None,
            match_keyword=None,
            min_anomaly_score=0.0,
            confidence_threshold=0.4,
        )
        incident = {"priority": "P3", "status": "New", "title": "テスト"}
        matched = self.svc.match_rules([rule], incident, 0.0)
        # 条件なし -> 基本信頼度 0.5
        assert len(matched) == 1
        assert matched[0][1] == 0.5

    def test_sorted_by_confidence(self):
        rule_high = make_rule(name="high_conf", match_priority="P1", confidence_threshold=0.5)
        rule_low = make_rule(
            name="low_conf", match_priority=None, match_keyword="X", confidence_threshold=0.3
        )
        incident = {"priority": "P1", "status": "New", "title": "テスト"}
        matched = self.svc.match_rules([rule_low, rule_high], incident, 0.0)
        # rule_high が先（信頼度高い）
        assert matched[0][0].name == "high_conf"


# ── RemediationService 実行テスト ──────────────────────────────────────────────


class TestRemediationExecution:
    def setup_method(self):
        self.svc = RemediationService()

    def _make_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()

        async def refresh_side_effect(obj):
            pass

        session.refresh = AsyncMock(side_effect=refresh_side_effect)
        return session

    @pytest.mark.asyncio
    async def test_run_remediation_success(self):
        session = self._make_session()
        rule = make_rule(requires_approval=False, confidence_threshold=0.7)
        incident_id = uuid.uuid4()

        log = await self.svc.run_remediation(
            session, incident_id, rule, confidence=0.9, dry_run=False
        )
        assert log.status == RemediationStatus.SUCCESS
        assert log.confidence_score == 0.9
        assert log.is_dry_run is False

    @pytest.mark.asyncio
    async def test_run_remediation_dry_run(self):
        session = self._make_session()
        rule = make_rule(requires_approval=False)
        incident_id = uuid.uuid4()

        log = await self.svc.run_remediation(
            session, incident_id, rule, confidence=0.85, dry_run=True
        )
        assert log.status == RemediationStatus.DRY_RUN
        assert log.is_dry_run is True
        assert "[DRY-RUN]" in (log.result_message or "")

    @pytest.mark.asyncio
    async def test_run_remediation_requires_approval(self):
        session = self._make_session()
        rule = make_rule(requires_approval=True)
        incident_id = uuid.uuid4()

        log = await self.svc.run_remediation(
            session, incident_id, rule, confidence=0.9, dry_run=False
        )
        assert log.status == RemediationStatus.AWAITING_APPROVAL

    @pytest.mark.asyncio
    async def test_run_remediation_with_action_params(self):
        session = self._make_session()
        params = json.dumps({"target": "web-service", "timeout": 30})
        rule = make_rule(action_params=params, requires_approval=False)
        incident_id = uuid.uuid4()

        log = await self.svc.run_remediation(
            session, incident_id, rule, confidence=0.9, dry_run=False
        )
        assert log.status == RemediationStatus.SUCCESS
        assert "web-service" in (log.result_message or "")

    @pytest.mark.asyncio
    async def test_approve_remediation(self):
        session = self._make_session()
        log = make_log(
            status=RemediationStatus.AWAITING_APPROVAL,
            action_type=RemediationActionType.RESTART_SERVICE,
            action_params=None,
        )

        approved_log = await self.svc.approve_remediation(
            session, log, approver="admin@example.com"
        )
        assert approved_log.status == RemediationStatus.SUCCESS
        assert approved_log.approved_by == "admin@example.com"

    @pytest.mark.asyncio
    async def test_approve_non_pending_raises(self):
        session = self._make_session()
        log = make_log(status=RemediationStatus.SUCCESS)

        with pytest.raises(ValueError, match="承認待ち状態ではありません"):
            await self.svc.approve_remediation(session, log, approver="admin")


# ── API エンドポイント テスト ─────────────────────────────────────────────────


class TestRemediationAPI:
    def setup_method(self):
        from fastapi.testclient import TestClient

        from src.main import app

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_list_rules_empty(self):
        """ルール一覧（DBなしでも200）"""
        with patch("src.api.v1.remediation._svc.get_rules", new=AsyncMock(return_value=[])):
            resp = self.client.get("/api/v1/remediation/rules")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_rule_not_found(self):
        """存在しないルール→404"""
        with patch("src.api.v1.remediation._svc.get_rule", new=AsyncMock(return_value=None)):
            resp = self.client.get(f"/api/v1/remediation/rules/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_list_logs_empty(self):
        """ログ一覧（DBなしでも200）"""
        with patch("src.api.v1.remediation._svc.get_logs", new=AsyncMock(return_value=[])):
            resp = self.client.get("/api/v1/remediation/logs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_log_not_found(self):
        """存在しないログ→404"""
        with patch("src.api.v1.remediation._svc.get_log", new=AsyncMock(return_value=None)):
            resp = self.client.get(f"/api/v1/remediation/logs/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_approve_log_not_found(self):
        """存在しないログ承認→404"""
        with patch("src.api.v1.remediation._svc.get_log", new=AsyncMock(return_value=None)):
            resp = self.client.post(
                f"/api/v1/remediation/logs/{uuid.uuid4()}/approve",
                json={"approver": "admin"},
            )
        assert resp.status_code == 404

    def test_trigger_incident_not_found(self):
        """存在しないインシデントでトリガー→404"""
        with patch("src.api.v1.remediation._svc.get_rules", new=AsyncMock(return_value=[])):
            resp = self.client.post(
                "/api/v1/remediation/trigger",
                json={"incident_id": str(uuid.uuid4()), "dry_run": True},
            )
        # DBなし環境では404または500 (テーブル未作成)
        assert resp.status_code in (404, 500)


# ── モデル定義 テスト ─────────────────────────────────────────────────────────


class TestRemediationModels:
    def test_status_enum(self):
        assert RemediationStatus.SUCCESS == "success"
        assert RemediationStatus.DRY_RUN == "dry_run"
        assert RemediationStatus.AWAITING_APPROVAL == "awaiting_approval"

    def test_action_type_enum(self):
        assert RemediationActionType.RESTART_SERVICE == "restart_service"
        assert RemediationActionType.SCALE_UP == "scale_up"
        assert RemediationActionType.RUN_PLAYBOOK == "run_playbook"

    def test_rule_model_fields(self):
        rule = RemediationRule()
        assert hasattr(rule, "rule_id")
        assert hasattr(rule, "name")
        assert hasattr(rule, "action_type")
        assert hasattr(rule, "confidence_threshold")
        assert hasattr(rule, "requires_approval")

    def test_log_model_fields(self):
        log = RemediationLog()
        assert hasattr(log, "log_id")
        assert hasattr(log, "incident_id")
        assert hasattr(log, "status")
        assert hasattr(log, "is_dry_run")
        assert hasattr(log, "confidence_score")
