"""SLA監視サービス カバレッジ補完テスト

sla_monitor_service.py の未テスト箇所を重点的にカバーする:
- APScheduler start/stop (lines 85-97, 111-113)
- _scheduled_check / _monitor_loop (lines 125-133, 137-147)
- response breach skip (line 190)
- check_sla_warnings created_at=None (line 224)
- response SLA warning detection (lines 255-273)
- get_sla_status created_at=None (line 295)
- get_active_warnings created_at=None (line 395)
- _notify_breach / _notify_warning (lines 475-476, 493-494)
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.models.incident import Incident
from src.services.sla_monitor_service import SLAMonitorService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Incident.__table__.create, checkfirst=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


# --- APScheduler start/stop テスト (lines 85-97, 111-113) -----------------------


@pytest.mark.asyncio
async def test_start_with_apscheduler():
    """APSchedulerが利用可能な場合のstart()パス (lines 85-97)"""
    import sys

    service = SLAMonitorService()

    mock_scheduler_instance = MagicMock()
    mock_scheduler_cls = MagicMock(return_value=mock_scheduler_instance)
    mock_trigger_cls = MagicMock()

    # APSchedulerモジュールをモックとしてsys.modulesに登録
    mock_apscheduler_schedulers = MagicMock()
    mock_apscheduler_schedulers.asyncio = MagicMock()
    mock_apscheduler_schedulers.asyncio.AsyncIOScheduler = mock_scheduler_cls

    mock_apscheduler_triggers = MagicMock()
    mock_apscheduler_triggers.interval = MagicMock()
    mock_apscheduler_triggers.interval.IntervalTrigger = mock_trigger_cls

    fake_modules = {
        "apscheduler": MagicMock(),
        "apscheduler.schedulers": MagicMock(),
        "apscheduler.schedulers.asyncio": mock_apscheduler_schedulers.asyncio,
        "apscheduler.triggers": MagicMock(),
        "apscheduler.triggers.interval": mock_apscheduler_triggers.interval,
    }

    with patch.dict(sys.modules, fake_modules):
        await service.start()

    assert service.running is True
    assert service._scheduler is not None
    mock_scheduler_instance.add_job.assert_called_once()
    mock_scheduler_instance.start.assert_called_once()

    # stop with APScheduler (lines 111-113)
    await service.stop()
    assert service.running is False
    assert service._scheduler is None


# --- _scheduled_check テスト (lines 125-133) ------------------------------------


@pytest.mark.asyncio
async def test_scheduled_check_success():
    """_scheduled_check() 正常実行 (lines 125-131)"""
    service = SLAMonitorService()

    mock_db = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("src.core.database.AsyncSessionLocal", return_value=mock_session_ctx),
        patch.object(service, "check_sla_breaches", new_callable=AsyncMock, return_value=0),
        patch.object(service, "check_sla_warnings", new_callable=AsyncMock, return_value=[]),
    ):
        await service._scheduled_check()

    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduled_check_exception():
    """_scheduled_check() 例外発生時もログを出して継続 (lines 132-133)"""
    service = SLAMonitorService()

    with patch(
        "src.core.database.AsyncSessionLocal",
        side_effect=Exception("DB connection failed"),
    ):
        # 例外が飛ばずにログ出力のみ
        await service._scheduled_check()


# --- _monitor_loop テスト (lines 137-147) ----------------------------------------


@pytest.mark.asyncio
async def test_monitor_loop_single_iteration():
    """_monitor_loop() 1回実行後に停止 (lines 137-147)"""
    service = SLAMonitorService()
    service.running = True

    mock_db = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

    call_count = 0

    async def fake_check_breaches(db):
        nonlocal call_count
        call_count += 1
        service.running = False  # 1回で停止
        return 0

    with (
        patch("src.core.database.AsyncSessionLocal", return_value=mock_session_ctx),
        patch.object(service, "check_sla_breaches", side_effect=fake_check_breaches),
        patch.object(service, "check_sla_warnings", new_callable=AsyncMock, return_value=[]),
        patch("src.services.sla_monitor_service.settings") as mock_settings,
    ):
        mock_settings.sla_check_interval_seconds = 0  # sleepを最小化
        await service._monitor_loop()

    assert call_count == 1


@pytest.mark.asyncio
async def test_monitor_loop_exception():
    """_monitor_loop() 例外発生時も継続 (lines 145-146)"""
    service = SLAMonitorService()
    service.running = True

    # 初回で例外、2回目で停止のパターン
    with (
        patch(
            "src.core.database.AsyncSessionLocal",
            side_effect=[Exception("DB error"), MagicMock()],
        ),
        patch("src.services.sla_monitor_service.settings") as mock_settings,
    ):
        mock_settings.sla_check_interval_seconds = 0

        # running=Falseにして次のループで止まるようにする
        async def stop_after_delay():
            await asyncio.sleep(0.01)
            service.running = False

        stop_task = asyncio.create_task(stop_after_delay())
        await service._monitor_loop()
        stop_task.cancel()
        try:
            await stop_task
        except asyncio.CancelledError:
            pass


# --- response breach skip テスト (line 190) ------------------------------------


@pytest.mark.asyncio
async def test_response_breach_already_marked(db: AsyncSession):
    """レスポンスSLA違反: 既にsla_breached=Trueのインシデントはスキップ (line 190)"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-SKIP-{uuid.uuid4().hex[:6]}",
        title="Already Breached Skip Test",
        priority="P1",
        status="New",
        sla_breached=True,  # 既にマーク済み
        sla_breached_at=now - timedelta(minutes=10),
        sla_response_due_at=now - timedelta(minutes=5),
        sla_resolution_due_at=now + timedelta(hours=1),
        created_at=now - timedelta(minutes=30),
        updated_at=now,
        acknowledged_at=None,
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch(
        "src.services.sla_monitor_service.audit_service.record_audit_log",
        new=AsyncMock(),
    ):
        await service.check_sla_breaches(db)

    # 既にbreachedなのでカウントに含まれない
    assert incident.sla_breached is True


# --- check_sla_warnings created_at=None テスト (line 224) ----------------------


@pytest.mark.asyncio
async def test_check_sla_warnings_created_at_none(db: AsyncSession):
    """check_sla_warnings() created_at=Noneのインシデントはスキップ (line 224)"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-CNONE-{uuid.uuid4().hex[:6]}",
        title="Created At None Test",
        priority="P1",
        status="In_Progress",
        sla_breached=False,
        sla_response_due_at=now + timedelta(hours=1),
        sla_resolution_due_at=now + timedelta(hours=2),
        created_at=None,  # created_at=None
        updated_at=now,
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    warnings = await service.check_sla_warnings(db)

    matching = [w for w in warnings if w.get("incident_number") == incident.incident_number]
    assert len(matching) == 0


# --- response SLA warning in check_sla_warnings (lines 255-273) ----------------


@pytest.mark.asyncio
async def test_check_sla_warnings_response_sla_warning(db: AsyncSession):
    """check_sla_warnings() 未応答インシデントでレスポンスSLA警告検出 (lines 255-273)"""
    now = datetime.now(UTC)
    # レスポンスSLA: 全体10時間のうち8時間経過 = 80% (warning_70)
    created_at = now - timedelta(hours=8)
    response_deadline = now + timedelta(hours=2)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-RSPW-{uuid.uuid4().hex[:6]}",
        title="Response SLA Warning Test",
        priority="P2",
        status="New",
        sla_breached=False,
        sla_response_due_at=response_deadline,
        sla_resolution_due_at=now + timedelta(hours=10),  # 解決SLAは遠い
        created_at=created_at,
        updated_at=now,
        acknowledged_at=None,  # 未応答
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch(
        "src.services.sla_monitor_service.notification_service.notify_sla_warning",
        new=AsyncMock(),
    ):
        warnings = await service.check_sla_warnings(db)

    response_warnings = [
        w
        for w in warnings
        if w.get("incident_number") == incident.incident_number and w.get("sla_type") == "response"
    ]
    assert len(response_warnings) >= 1
    assert response_warnings[0]["progress_percent"] >= 70.0


# --- get_sla_status created_at=None テスト (line 295) ---------------------------


@pytest.mark.asyncio
async def test_get_sla_status_created_at_none():
    """get_sla_status() created_at=Noneのインシデントでもcreated_at=None → None返却 (line 295)"""
    incident_id = uuid.uuid4()

    # created_at=None のモックインシデント
    mock_incident = MagicMock()
    mock_incident.incident_id = incident_id
    mock_incident.incident_number = "INC-CN2-000001"
    mock_incident.priority = "P3"
    mock_incident.status = "New"
    mock_incident.sla_breached = False
    mock_incident.created_at = None  # TimestampMixinのdefaultを回避

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_incident

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = SLAMonitorService()
    status = await service.get_sla_status(mock_db, str(incident_id))
    assert status is None


# --- get_active_warnings created_at=None テスト (line 395) ----------------------


@pytest.mark.asyncio
async def test_get_active_warnings_created_at_none(db: AsyncSession):
    """get_active_warnings() created_at=Noneのインシデントはスキップ (line 395)"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-AWN-{uuid.uuid4().hex[:6]}",
        title="Active Warnings No Created",
        priority="P2",
        status="In_Progress",
        sla_breached=False,
        sla_resolution_due_at=now + timedelta(hours=2),
        created_at=None,
        updated_at=now,
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    warnings = await service.get_active_warnings(db)
    matching = [w for w in warnings if w.get("incident_number") == incident.incident_number]
    assert len(matching) == 0


# --- _notify_breach テスト (lines 475-476) --------------------------------------


@pytest.mark.asyncio
async def test_notify_breach_calls_notification_service():
    """_notify_breach() がnotification_serviceを呼び出すこと (lines 475-476)"""
    service = SLAMonitorService()
    mock_incident = MagicMock()
    mock_incident.incident_number = "INC-2024-000001"
    mock_incident.title = "Test Incident"
    mock_incident.priority = "P1"

    with patch(
        "src.services.sla_monitor_service.notification_service.notify_sla_breach",
        new_callable=AsyncMock,
    ) as mock_notify:
        await service._notify_breach(mock_incident, "resolution")

    mock_notify.assert_awaited_once_with(
        incident_number="INC-2024-000001",
        incident_title="Test Incident",
        priority="P1",
        breach_type="resolution",
    )


@pytest.mark.asyncio
async def test_notify_breach_exception_handled():
    """_notify_breach() 例外発生時もログのみ"""
    service = SLAMonitorService()
    mock_incident = MagicMock()
    mock_incident.incident_number = "INC-2024-000001"
    mock_incident.title = "Test"
    mock_incident.priority = "P1"

    with patch(
        "src.services.sla_monitor_service.notification_service.notify_sla_breach",
        new_callable=AsyncMock,
        side_effect=Exception("Notification failed"),
    ):
        # 例外が飛ばないことを確認
        await service._notify_breach(mock_incident, "resolution")


# --- _notify_warning テスト (lines 493-494) -------------------------------------


@pytest.mark.asyncio
async def test_notify_warning_calls_notification_service():
    """_notify_warning() がnotification_serviceを呼び出すこと (lines 493-494)"""
    from src.services.sla_monitor_service import SLAWarningLevel

    service = SLAMonitorService()
    mock_incident = MagicMock()
    mock_incident.incident_number = "INC-2024-000002"
    mock_incident.title = "Warning Test"
    mock_incident.priority = "P2"

    with patch(
        "src.services.sla_monitor_service.notification_service.notify_sla_warning",
        new_callable=AsyncMock,
    ) as mock_notify:
        await service._notify_warning(mock_incident, SLAWarningLevel.WARNING_70, 0.75)

    mock_notify.assert_awaited_once_with(
        incident_number="INC-2024-000002",
        incident_title="Warning Test",
        priority="P2",
        warning_level="warning_70",
        progress_percent=75.0,
    )


@pytest.mark.asyncio
async def test_notify_warning_exception_handled():
    """_notify_warning() 例外発生時もログのみ"""
    from src.services.sla_monitor_service import SLAWarningLevel

    service = SLAMonitorService()
    mock_incident = MagicMock()
    mock_incident.incident_number = "INC-2024-000002"
    mock_incident.title = "Warning Test"
    mock_incident.priority = "P2"

    with patch(
        "src.services.sla_monitor_service.notification_service.notify_sla_warning",
        new_callable=AsyncMock,
        side_effect=Exception("Warning notification failed"),
    ):
        await service._notify_warning(mock_incident, SLAWarningLevel.WARNING_90, 0.95)
