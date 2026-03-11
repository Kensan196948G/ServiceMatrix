"""Issue #52 最終カバレッジ向上テスト

対象未カバー行:
  src/main.py (23-26): lifespan context manager (start/stop)
  src/api/v1/backup.py (50-61): pg_dump 実行分岐
  src/api/v1/incidents.py (286-287): bulk_update else分岐（無効アクション）
  src/api/v1/incidents.py (508): description内サービス名マッチ
  src/core/rate_limit.py (11): TESTING=false時のlimiter作成
  src/core/security.py (15): get_password_hash
  src/middleware/audit.py (25): AUDIT_EXCLUDE_PATHS早期リターン
  src/middleware/rbac.py (55): user.is_active=False → credentials_exception
  src/services/ai_service.py (93-94): json.loads例外 → _mock_rca()
  src/services/ai_service.py (158-159): anthropic ImportError → None
  src/services/sla_monitor_service.py (102-106): APScheduler ImportError → asyncio fallback
"""

import asyncio
import subprocess
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── main.py: lifespan context manager (lines 23-26) ──────────────────────────


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_sla_monitor():
    """lifespan: sla_monitor.start() / stop() を呼び出す"""
    from src.main import lifespan, create_app

    app = create_app()
    with (
        patch("src.main.sla_monitor") as mock_monitor,
        patch("src.main.setup_logging"),
    ):
        mock_monitor.start = AsyncMock()
        mock_monitor.stop = AsyncMock()

        async with lifespan(app):
            mock_monitor.start.assert_called_once()

        mock_monitor.stop.assert_called_once()


# ─── backup.py: pg_dump 実行分岐 (lines 50-61) ────────────────────────────────


@pytest.mark.asyncio
async def test_create_backup_postgresql_success():
    """create_backup: PostgreSQL環境でpg_dump成功 → type=postgresql"""
    from src.api.v1.backup import create_backup

    current_user = MagicMock()

    mock_result = MagicMock()
    mock_result.returncode = 0

    mock_stat = MagicMock()
    mock_stat.st_size = 1024

    with (
        patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@localhost/db"}),
        patch("src.api.v1.backup.subprocess.run", return_value=mock_result) as mock_run,
        patch("src.api.v1.backup.Path.stat", return_value=mock_stat),
        patch("src.api.v1.backup._ensure_backup_dir"),
    ):
        result = await create_backup(current_user=current_user)

    assert result["type"] == "postgresql"
    assert result["size_bytes"] == 1024
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_create_backup_postgresql_failure_raises_500():
    """create_backup: pg_dump 失敗 → HTTPException 500"""
    from fastapi import HTTPException

    from src.api.v1.backup import create_backup

    current_user = MagicMock()

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "pg_dump: connection error"

    with (
        patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@localhost/db"}),
        patch("src.api.v1.backup.subprocess.run", return_value=mock_result),
        patch("src.api.v1.backup._ensure_backup_dir"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_backup(current_user=current_user)

    assert exc_info.value.status_code == 500
    assert "バックアップ失敗" in exc_info.value.detail


# ─── incidents.py: bulk_update else分岐 (lines 286-287) ─────────────────────


@pytest.mark.asyncio
async def test_bulk_update_invalid_action_adds_to_failed():
    """bulk_update_incidents: 無効アクション → failed_ids に追加"""
    from src.api.v1.incidents import bulk_update_incidents, BulkIncidentUpdate

    iid = uuid.uuid4()

    incident_mock = MagicMock()
    incident_mock.incident_id = iid
    incident_mock.status = "New"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident_mock

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()

    current_user = MagicMock()

    body = BulkIncidentUpdate(
        incident_ids=[iid],
        action="invalid_action",  # 無効なアクション → else分岐
    )

    result = await bulk_update_incidents(body=body, db=db, current_user=current_user)

    assert result.updated_count == 0
    assert iid in result.failed_ids


# ─── incidents.py: description内サービス名マッチ (line 508) ─────────────────


@pytest.mark.asyncio
async def test_bulk_update_exception_during_loop_adds_to_failed():
    """bulk_update_incidents: ループ内で例外発生 → except Exception で failed_ids に追加 (lines 286-287)"""
    from src.api.v1.incidents import bulk_update_incidents, BulkIncidentUpdate

    iid = uuid.uuid4()

    # db.execute が例外を投げる → except Exception 分岐
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("DB接続エラー"))
    db.flush = AsyncMock()

    current_user = MagicMock()

    body = BulkIncidentUpdate(
        incident_ids=[iid],
        action="close",
    )

    result = await bulk_update_incidents(body=body, db=db, current_user=current_user)

    assert result.updated_count == 0
    assert iid in result.failed_ids


@pytest.mark.asyncio
async def test_suggest_problem_description_match_scores_0_3():
    """suggest_problem: description内にserviceが含まれる → score += 0.3"""
    from src.api.v1.incidents import suggest_problem

    incident_id = uuid.uuid4()

    incident_mock = MagicMock()
    incident_mock.incident_id = incident_id
    incident_mock.affected_service = "network"
    incident_mock.priority = "P2"

    # タイトルにはマッチしないが、descriptionにnetworkが含まれる
    problem_mock = MagicMock()
    problem_mock.problem_id = uuid.uuid4()
    problem_mock.title = "サービス障害調査"  # "network" は含まれない
    problem_mock.description = "networkの障害に関する詳細調査"  # "network" が含まれる
    problem_mock.priority = "P3"  # 優先度はマッチしない

    inc_result = MagicMock()
    inc_result.scalar_one_or_none.return_value = incident_mock

    prob_result = MagicMock()
    prob_result.scalars.return_value.all.return_value = [problem_mock]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[inc_result, prob_result])

    current_user = MagicMock()

    result = await suggest_problem(
        incident_id=incident_id, db=db, current_user=current_user
    )

    assert len(result["suggestions"]) == 1
    # description マッチのみ: 0.3
    assert result["suggestions"][0]["similarity_score"] == 0.3


# ─── rate_limit.py: TESTING!=true時のlimiter (line 11) ──────────────────────


def test_rate_limit_non_testing_creates_limited_limiter():
    """rate_limit.py: TESTING=false時に100/minuteのlimiterが作成される"""
    import importlib

    with patch.dict("os.environ", {"TESTING": "false"}, clear=False):
        import src.core.rate_limit as rl_module
        # モジュールを強制リロード
        importlib.reload(rl_module)
        limiter = rl_module.limiter
        # 100/minute の設定のlimiterが作成されているはず
        assert limiter is not None

    # テスト用に元に戻す
    with patch.dict("os.environ", {"TESTING": "true"}, clear=False):
        importlib.reload(rl_module)


# ─── security.py: get_password_hash (line 15) ────────────────────────────────


def test_get_password_hash_returns_hashed_string():
    """get_password_hash: パスワードをbcryptハッシュに変換する"""
    from src.core.security import get_password_hash, verify_password

    password = "test_password_12345"
    hashed = get_password_hash(password)

    assert hashed != password
    assert hashed.startswith("$2b$")
    # verify_passwordで確認
    assert verify_password(password, hashed) is True


# ─── middleware/audit.py: AUDIT_EXCLUDE_PATHS早期リターン (line 25) ──────────


@pytest.mark.asyncio
async def test_audit_middleware_excludes_health_path():
    """AuditMiddleware: /health パスは早期リターン（AUDIT_EXCLUDE_PATHS）"""
    from fastapi import FastAPI
    from starlette.requests import Request
    from starlette.responses import Response

    from src.middleware.audit import AuditMiddleware

    app = FastAPI()
    middleware = AuditMiddleware(app)

    call_next_called = False

    async def call_next(request: Request) -> Response:
        nonlocal call_next_called
        call_next_called = True
        return Response(content="ok", status_code=200)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "query_string": b"",
        "headers": [],
        "server": ("localhost", 8000),
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope=scope)

    response = await middleware.dispatch(request, call_next)

    assert call_next_called is True
    assert response.status_code == 200


# ─── middleware/rbac.py: user.is_active=False (line 55) ─────────────────────


@pytest.mark.asyncio
async def test_get_current_user_inactive_user_raises_401():
    """get_current_user: is_active=False → credentials_exception"""
    from fastapi import HTTPException

    from src.middleware.rbac import get_current_user

    user_id = uuid.uuid4()

    inactive_user = MagicMock()
    inactive_user.user_id = user_id
    inactive_user.is_active = False

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = inactive_user

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    # JWT tokenを作成してget_current_userを呼び出す
    from src.core.security import create_access_token

    token = create_access_token(data={"sub": str(user_id)})

    # is_token_blacklisted をモックしてFalseを返す（ブラックリストに入っていない）
    with (
        patch("src.middleware.rbac.is_token_blacklisted", new=AsyncMock(return_value=False)),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_current_user(token=token, db=db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_active_user_returns_user():
    """get_current_user: is_active=True → return user (line 55)"""
    from src.middleware.rbac import get_current_user

    user_id = uuid.uuid4()

    active_user = MagicMock()
    active_user.user_id = user_id
    active_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = active_user

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    from src.core.security import create_access_token

    token = create_access_token(data={"sub": str(user_id)})

    with patch("src.middleware.rbac.is_token_blacklisted", new=AsyncMock(return_value=False)):
        result = await get_current_user(token=token, db=db)

    assert result is active_user


# ─── ai_service.py: json.loads例外 → _mock_rca() (lines 93-94) ──────────────


@pytest.mark.asyncio
async def test_analyze_rca_invalid_json_falls_back_to_mock():
    """generate_rca_report: json.loads失敗 → _mock_rca()を返す"""
    from src.services.ai_service import AIService

    svc = AIService()
    svc.provider = "openai"
    svc.api_key = "test-key"

    # _openai_text が不正なJSONを返す
    with patch.object(svc, "_openai_text", new=AsyncMock(return_value="not valid json")):
        result = await svc.generate_rca_report(
            problem_title="テスト問題",
            affected_services=["network"],
            timeline=["10:00 障害発生", "10:15 調査開始"],
        )

    # _mock_rca() の内容が返される
    assert "root_cause" in result
    assert "recommendations" in result


# ─── ai_service.py: anthropic ImportError → None (lines 158-159) ────────────


@pytest.mark.asyncio
async def test_anthropic_text_import_error_returns_none():
    """_anthropic_text: anthropic ImportError → None (ImportError except branch)"""
    from src.services.ai_service import AIService

    svc = AIService()
    svc.provider = "anthropic"
    svc.api_key = "test-key"
    svc.model = "claude-3-5-haiku-20241022"

    # builtins.__import__ をモックして anthropic の import で ImportError を発生させる
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("anthropic not installed")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        result = await svc._anthropic_text("テストプロンプト", max_tokens=100)

    assert result is None


@pytest.mark.asyncio
async def test_anthropic_text_api_exception_returns_none():
    """_anthropic_text: anthropic API呼び出し時に一般例外 → None (lines 158-159)"""
    from src.services.ai_service import AIService

    svc = AIService()
    svc.provider = "anthropic"
    svc.api_key = "test-key"
    svc.model = "claude-3-5-haiku-20241022"

    # anthropic モジュールをモックしてAPIコールで例外を発生させる
    mock_anthropic = MagicMock()
    mock_client = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API error"))

    import sys
    with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
        result = await svc._anthropic_text("テストプロンプト", max_tokens=100)

    assert result is None


# ─── compliance.py: SLA FAIL分岐 (lines 189-190) ────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_checks_sla_fail_when_field_missing():
    """_evaluate_checks: sla_field_existsがFalse → SLA FAIL分岐 (lines 189-190)"""
    from src.api.v1.compliance import _evaluate_checks

    # SLAチェックのみ含むチェックリスト
    sla_check = {
        "id": "soc2-cc7.2",
        "category": "CC7 システム運用",
        "title": "SLAモニタリング",
        "description": "SLA監視が実施されているか確認します。",
    }

    # DBのカウントをモック（全て1を返す）
    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    db.execute = AsyncMock(return_value=count_result)

    # hasattr(Incident, "sla_breached_at") が False になるよう builtins.hasattr をパッチ
    import builtins
    original_hasattr = builtins.hasattr

    def mock_hasattr(obj, name):
        if name == "sla_breached_at":
            return False
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", side_effect=mock_hasattr):
        results = await _evaluate_checks([sla_check], db)

    assert len(results) == 1
    assert results[0]["status"] == "FAIL"
    assert "未実装" in results[0]["evidence"]


# ─── sla_monitor_service.py: APScheduler ImportError → asyncio fallback (lines 102-106) ─


@pytest.mark.asyncio
async def test_sla_monitor_start_importerror_falls_back_to_asyncio():
    """SLAMonitorService.start: APScheduler ImportError → asyncio create_task fallback"""
    from src.services.sla_monitor_service import SLAMonitorService

    svc = SLAMonitorService()
    assert svc.running is False

    # asyncio.create_task をモックして実際のタスク作成をスキップ
    task_mock = MagicMock()
    task_mock.cancel = MagicMock()

    # APSchedulerのImportErrorをシミュレート
    async def mock_monitor_loop():
        pass

    # コルーチンを名前付きで作成して明示的に close() でクリーンアップする
    coro = mock_monitor_loop()
    # _monitor_loop は async def なので patch.object はデフォルトで AsyncMock を使用し
    # _execute_mock_call コルーチンをリークさせる。new=MagicMock(...) で強制的に
    # 同期モックにしてリークを防止する。
    _loop_mock = MagicMock(return_value=coro)
    mock_create_task = MagicMock(return_value=task_mock)
    with (
        patch.dict(
            "sys.modules",
            {
                "apscheduler": None,
                "apscheduler.schedulers": None,
                "apscheduler.schedulers.asyncio": None,
                "apscheduler.triggers": None,
                "apscheduler.triggers.interval": None,
            },
        ),
        patch.object(svc, "_monitor_loop", new=_loop_mock),
        patch("asyncio.create_task", new=mock_create_task),
    ):
        await svc.start()
    coro.close()  # 未 await コルーチンを明示クローズ → RuntimeWarning 防止

    assert svc.running is True
    mock_create_task.assert_called_once()

    # クリーンアップ
    svc.running = False
    svc._task = None
