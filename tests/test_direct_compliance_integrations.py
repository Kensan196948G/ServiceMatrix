"""compliance.py / integrations.py 直接呼び出しテスト - カバレッジ向上

対象: src/api/v1/compliance.py (71%), src/api/v1/integrations.py (74%)
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_count_execute(counts: list[int]):
    """_evaluate_checks が呼ぶ 4回の db.execute をモック (count返却)"""
    results = []
    for c in counts:
        r = MagicMock()
        r.scalar_one.return_value = c
        results.append(r)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    return db


def _make_cfg(
    config_id=None,
    integration_type="jira",
    name="Jira統合",
    is_active=True,
):
    cfg = MagicMock()
    cfg.config_id = config_id or uuid.uuid4()
    cfg.integration_type = integration_type
    cfg.name = name
    cfg.base_url = "https://example.atlassian.net"
    cfg.username = "admin"
    cfg.is_active = is_active
    cfg.sync_interval_minutes = 30
    cfg.last_synced_at = None
    cfg.created_at = datetime.now(UTC)
    return cfg


# ─── compliance.py: _evaluate_checks FAIL分岐 ──────────────────────────────────


async def test_evaluate_checks_all_fail_counts_zero():
    """_evaluate_checks: 全カウント0 → インシデント・変更管理・CMDB が FAIL"""
    from src.api.v1.compliance import get_soc2_checks

    # user_count=0, change_count=0, incident_count=0, ci_count=0
    db = _make_count_execute([0, 0, 0, 0])
    current_user = MagicMock()

    result = await get_soc2_checks(db=db, current_user=current_user)

    checks = result["checks"]
    summary = result["summary"]

    # 少なくとも1つ以上のFAILが存在する
    fail_checks = [c for c in checks if c["status"] == "FAIL"]
    assert len(fail_checks) > 0
    assert summary["fail"] > 0
    assert "checks" in result
    assert "summary" in result


async def test_evaluate_checks_all_pass_counts_nonzero():
    """_evaluate_checks: 全カウント>0 → 自動評価可能なチェックが PASS"""
    from src.api.v1.compliance import get_soc2_checks

    # user_count=5, change_count=10, incident_count=3, ci_count=7
    db = _make_count_execute([5, 10, 3, 7])
    current_user = MagicMock()

    result = await get_soc2_checks(db=db, current_user=current_user)

    checks = result["checks"]
    pass_checks = [c for c in checks if c["status"] == "PASS"]
    assert len(pass_checks) > 0
    assert result["summary"]["pass"] > 0


async def test_get_soc2_checks_returns_structure():
    """get_soc2_checks: checks と summary を含む dict を返す"""
    from src.api.v1.compliance import get_soc2_checks

    db = _make_count_execute([1, 1, 1, 1])
    current_user = MagicMock()

    result = await get_soc2_checks(db=db, current_user=current_user)

    assert "checks" in result
    assert "summary" in result
    summary = result["summary"]
    assert "total" in summary
    assert "pass" in summary
    assert "fail" in summary
    assert "score" in summary


async def test_get_iso27001_checks_returns_structure():
    """get_iso27001_checks: checks と summary を含む dict を返す"""
    from src.api.v1.compliance import get_iso27001_checks

    db = _make_count_execute([2, 5, 8, 3])
    current_user = MagicMock()

    result = await get_iso27001_checks(db=db, current_user=current_user)

    assert "checks" in result
    assert "summary" in result
    assert result["summary"]["total"] > 0


async def test_get_iso27001_checks_user_access_management():
    """get_iso27001_checks: ユーザーアクセス管理 → user_count=0 で FAIL"""
    from src.api.v1.compliance import get_iso27001_checks

    # user_count=0 → ユーザーアクセス管理が FAIL
    db = _make_count_execute([0, 0, 0, 0])
    current_user = MagicMock()

    result = await get_iso27001_checks(db=db, current_user=current_user)

    # ユーザーアクセス管理チェックが存在し、FAILになる
    user_checks = [c for c in result["checks"] if "ユーザーアクセス管理" in c["title"]]
    if user_checks:
        assert user_checks[0]["status"] == "FAIL"


async def test_get_compliance_report_returns_both_frameworks():
    """get_compliance_report: SOC2 + ISO27001 を含む統合レポート"""
    from src.api.v1.compliance import get_compliance_report

    # _evaluate_checks が2回呼ばれる（SOC2 + ISO27001）→ 8回のdb.execute
    db = _make_count_execute([1, 1, 1, 1, 1, 1, 1, 1])
    current_user = MagicMock()

    result = await get_compliance_report(db=db, current_user=current_user)

    assert "soc2" in result
    assert "iso27001" in result
    assert "overall" in result
    assert "checks" in result["soc2"]
    assert "summary" in result["soc2"]
    assert "checks" in result["iso27001"]


async def test_get_compliance_report_fail_counts_zero():
    """get_compliance_report: カウント0 → FAIL チェックが含まれる"""
    from src.api.v1.compliance import get_compliance_report

    db = _make_count_execute([0, 0, 0, 0, 0, 0, 0, 0])
    current_user = MagicMock()

    result = await get_compliance_report(db=db, current_user=current_user)

    soc2_fails = [c for c in result["soc2"]["checks"] if c["status"] == "FAIL"]
    assert len(soc2_fails) > 0


async def test_build_summary_empty_list():
    """_build_summary: checks が空 → score=0 を返す"""
    from src.api.v1.compliance import _build_summary

    result = _build_summary([])
    assert result["score"] == 0
    assert result["total"] == 0


async def test_build_summary_all_pass():
    """_build_summary: 全 PASS → score=100"""
    from src.api.v1.compliance import _build_summary

    checks = [{"status": "PASS"}, {"status": "PASS"}]
    result = _build_summary(checks)
    assert result["score"] == 100
    assert result["pass"] == 2
    assert result["fail"] == 0


async def test_build_summary_mixed():
    """_build_summary: 混在 → score 計算"""
    from src.api.v1.compliance import _build_summary

    checks = [
        {"status": "PASS"},
        {"status": "FAIL"},
        {"status": "MANUAL"},
    ]
    result = _build_summary(checks)
    assert result["total"] == 3
    assert result["pass"] == 1
    assert result["fail"] == 1
    assert result["manual"] == 1
    # score = round(1/3 * 100) = 33
    assert result["score"] == 33


# ─── integrations.py ───────────────────────────────────────────────────────────


async def test_list_integrations_returns_list():
    """list_integrations: 設定一覧を返す（line 71）"""
    from src.api.v1.integrations import list_integrations

    cfg = _make_cfg()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [cfg]
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    current_user = MagicMock()

    result = await list_integrations(db=db, current_user=current_user)

    assert len(result) == 1
    assert result[0]["name"] == "Jira統合"
    assert "config_id" in result[0]


async def test_list_integrations_empty():
    """list_integrations: 空リスト"""
    from src.api.v1.integrations import list_integrations

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    result = await list_integrations(db=db, current_user=MagicMock())
    assert result == []


async def test_create_integration_success():
    """create_integration: 正常作成（line 83-84）"""
    from src.api.v1.integrations import create_integration, IntegrationCreate

    db = AsyncMock()
    db.add = MagicMock()

    cfg_instance = _make_cfg(name="ServiceNow統合")
    db.refresh = AsyncMock(side_effect=lambda x: None)

    with patch("src.api.v1.integrations.IntegrationConfig", return_value=cfg_instance):
        data = IntegrationCreate(
            integration_type="servicenow",
            name="ServiceNow統合",
        )
        current_user = MagicMock()
        result = await create_integration(payload=data, db=db, current_user=current_user)

    db.add.assert_called_once()
    db.commit.assert_called_once()


async def test_update_integration_not_found_raises_404():
    """update_integration: 設定不存在 → 404（lines 95-96）"""
    from src.api.v1.integrations import update_integration, IntegrationUpdate

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await update_integration(
            config_id=uuid.uuid4(),
            payload=IntegrationUpdate(name="更新"),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_update_integration_success():
    """update_integration: 正常更新（lines 97-101）"""
    from src.api.v1.integrations import update_integration, IntegrationUpdate

    cfg = _make_cfg(name="旧名称")
    db = AsyncMock()
    db.get = AsyncMock(return_value=cfg)

    result = await update_integration(
        config_id=cfg.config_id,
        payload=IntegrationUpdate(name="新名称"),
        db=db,
        current_user=MagicMock(),
    )

    assert cfg.name == "新名称"
    db.commit.assert_called_once()


async def test_delete_integration_not_found_raises_404():
    """delete_integration: 設定不存在 → 404（lines 111-112）"""
    from src.api.v1.integrations import delete_integration

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await delete_integration(
            config_id=uuid.uuid4(),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_delete_integration_success():
    """delete_integration: 正常削除（lines 113-114）"""
    from src.api.v1.integrations import delete_integration

    cfg = _make_cfg()
    db = AsyncMock()
    db.get = AsyncMock(return_value=cfg)

    result = await delete_integration(
        config_id=cfg.config_id,
        db=db,
        current_user=MagicMock(),
    )

    db.delete.assert_called_once_with(cfg)
    db.commit.assert_called_once()
    assert result is None


async def test_test_integration_not_found_raises_404():
    """test_integration: 設定不存在 → 404（lines 124-125）"""
    from src.api.v1.integrations import test_integration

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await test_integration(
            config_id=uuid.uuid4(),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_test_integration_success():
    """test_integration: 正常 → success=True（line 127）"""
    from src.api.v1.integrations import test_integration

    cfg = _make_cfg(name="Jira")
    db = AsyncMock()
    db.get = AsyncMock(return_value=cfg)

    result = await test_integration(
        config_id=cfg.config_id,
        db=db,
        current_user=MagicMock(),
    )

    assert result["success"] is True
    assert "latency_ms" in result
    assert "Jira" in result["message"]


async def test_get_sync_log_not_found_raises_404():
    """get_sync_log: 設定不存在 → 404（lines 141-142）"""
    from src.api.v1.integrations import get_sync_log

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_sync_log(
            config_id=uuid.uuid4(),
            db=db,
            current_user=MagicMock(),
        )

    assert exc_info.value.status_code == 404


async def test_get_sync_log_success():
    """get_sync_log: 正常 → ダミーログ返却（line 144）"""
    from src.api.v1.integrations import get_sync_log

    cfg = _make_cfg()
    db = AsyncMock()
    db.get = AsyncMock(return_value=cfg)

    result = await get_sync_log(
        config_id=cfg.config_id,
        db=db,
        current_user=MagicMock(),
    )

    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0]["status"] == "success"
    assert "timestamp" in result[0]
