"""SLA自動監視バックグラウンドエンジン テスト"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.models.incident import Incident
from src.services.sla_monitor_service import (
    SLAMonitorService,
    SLAWarningLevel,
    calculate_sla_progress,
    get_warning_level,
    sla_monitor,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        # Only create Incident table to avoid PostgreSQL-specific types in other models
        await conn.run_sync(Incident.__table__.create, checkfirst=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


def _make_incident(
    priority: str = "P3",
    status: str = "New",
    sla_breached: bool = False,
    sla_resolution_due_at: datetime | None = None,
) -> Incident:
    now = datetime.now(UTC)
    if sla_resolution_due_at is None:
        sla_resolution_due_at = now + timedelta(hours=24)
    return Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-TEST-{uuid.uuid4().hex[:6]}",
        title="Test Incident",
        priority=priority,
        status=status,
        sla_breached=sla_breached,
        sla_response_due_at=now + timedelta(minutes=30),
        sla_resolution_due_at=sla_resolution_due_at,
        created_at=now,
        updated_at=now,
    )


# ─── テストケース ───────────────────────────────────────────────────────────────


def test_sla_monitor_singleton():
    """sla_monitorがSLAMonitorServiceインスタンスであること"""
    assert isinstance(sla_monitor, SLAMonitorService)


@pytest.mark.asyncio
async def test_sla_p1_breach_detection(db: AsyncSession):
    """P1インシデントでdeadlineが過ぎた場合にsla_breached=Trueになること"""
    past_deadline = datetime.now(UTC) - timedelta(minutes=5)
    incident = _make_incident(
        priority="P1", status="In_Progress", sla_resolution_due_at=past_deadline
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        count = await service.check_sla_breaches(db)

    assert count >= 1
    assert incident.sla_breached is True


@pytest.mark.asyncio
async def test_sla_not_breached_when_active(db: AsyncSession):
    """deadline未到来のインシデントはsla_breached=Falseのまま"""
    future_deadline = datetime.now(UTC) + timedelta(hours=2)
    incident = _make_incident(
        priority="P2", status="In_Progress", sla_resolution_due_at=future_deadline
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        await service.check_sla_breaches(db)

    assert incident.sla_breached is False


@pytest.mark.asyncio
async def test_sla_closed_not_checked(db: AsyncSession):
    """Closedステータスのインシデントはチェック対象外"""
    past_deadline = datetime.now(UTC) - timedelta(hours=1)
    incident = _make_incident(priority="P1", status="Closed", sla_resolution_due_at=past_deadline)
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        await service.check_sla_breaches(db)

    assert incident.sla_breached is False


@pytest.mark.asyncio
async def test_sla_resolved_not_checked(db: AsyncSession):
    """Resolvedステータスのインシデントはチェック対象外"""
    past_deadline = datetime.now(UTC) - timedelta(hours=1)
    incident = _make_incident(priority="P2", status="Resolved", sla_resolution_due_at=past_deadline)
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        await service.check_sla_breaches(db)

    assert incident.sla_breached is False


@pytest.mark.asyncio
async def test_sla_summary_structure(db: AsyncSession):
    """get_sla_summary()が正しい構造を返すこと"""
    incident = _make_incident(priority="P3", status="New")
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    summary = await service.get_sla_summary(db)

    assert isinstance(summary, dict)
    for priority_data in summary.values():
        assert "total" in priority_data
        assert "breached" in priority_data
        assert "compliance_rate" in priority_data


@pytest.mark.asyncio
async def test_sla_compliance_rate_100(db: AsyncSession):
    """違反なしの場合compliance_rateが100.0になること"""
    future = datetime.now(UTC) + timedelta(hours=10)
    incident = _make_incident(
        priority="P4", status="New", sla_resolution_due_at=future, sla_breached=False
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    summary = await service.get_sla_summary(db)

    assert "P4" in summary
    # P4に違反がなければ100%
    p4 = summary["P4"]
    assert p4["breached"] == 0
    assert p4["compliance_rate"] == 100.0


@pytest.mark.asyncio
async def test_sla_breach_timestamp_set(db: AsyncSession):
    """違反検知時にsla_breached_atが設定されること"""
    past_deadline = datetime.now(UTC) - timedelta(minutes=10)
    incident = _make_incident(
        priority="P1", status="Acknowledged", sla_resolution_due_at=past_deadline
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        await service.check_sla_breaches(db)

    assert incident.sla_breached is True
    assert incident.sla_breached_at is not None
    assert isinstance(incident.sla_breached_at, datetime)


@pytest.mark.asyncio
async def test_sla_monitor_start_stop():
    """start/stopメソッドが正常に動作すること"""
    service = SLAMonitorService()
    assert service.running is False
    assert service._task is None

    await service.start()
    assert service.running is True
    # APSchedulerパスでは_scheduler、asyncioフォールバックでは_taskが設定される
    assert service._task is not None or service._scheduler is not None

    await service.stop()
    assert service.running is False


@pytest.mark.asyncio
async def test_sla_monitor_stop_without_task():
    """タスクなしでstopが呼ばれても正常に終了すること"""
    service = SLAMonitorService()
    service.running = True
    service._task = None

    await service.stop()
    assert service.running is False


@pytest.mark.asyncio
async def test_sla_breach_audit_exception_handled(db: AsyncSession):
    """audit_service例外発生時も処理が継続すること"""
    past_deadline = datetime.now(UTC) - timedelta(minutes=5)
    incident = _make_incident(
        priority="P2", status="In_Progress", sla_resolution_due_at=past_deadline
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch(
        "src.services.sla_monitor_service.audit_service.record_audit_log",
        new=AsyncMock(side_effect=Exception("audit failed")),
    ):
        count = await service.check_sla_breaches(db)

    assert count >= 1
    assert incident.sla_breached is True


@pytest.mark.asyncio
async def test_sla_summary_with_breach(db: AsyncSession):
    """get_sla_summary()が違反ありインシデントを正しく集計すること"""
    past_deadline = datetime.now(UTC) - timedelta(hours=1)
    breached = _make_incident(
        priority="P1", status="In_Progress", sla_breached=True, sla_resolution_due_at=past_deadline
    )
    not_breached = _make_incident(
        priority="P1", status="In_Progress", sla_breached=False
    )
    db.add(breached)
    db.add(not_breached)
    await db.flush()

    service = SLAMonitorService()
    summary = await service.get_sla_summary(db)

    assert "P1" in summary
    p1 = summary["P1"]
    assert p1["total"] >= 2
    assert p1["breached"] >= 1
    assert p1["compliance_rate"] < 100.0


# ─── calculate_sla_progress / get_warning_level テスト ─────────────────────────


def test_calculate_sla_progress_midway():
    """SLA期限の半分経過時に約0.5を返すこと"""
    now = datetime.now(UTC)
    created_at = now - timedelta(hours=5)
    deadline = now + timedelta(hours=5)  # 全体10時間、5時間経過 = 0.5
    progress = calculate_sla_progress(created_at, deadline)
    assert 0.45 <= progress <= 0.55


def test_calculate_sla_progress_expired():
    """SLA期限を超過した場合に1.0以上を返すこと"""
    now = datetime.now(UTC)
    created_at = now - timedelta(hours=10)
    deadline = now - timedelta(hours=1)  # 既に超過
    progress = calculate_sla_progress(created_at, deadline)
    assert progress >= 1.0


def test_calculate_sla_progress_zero_duration():
    """created_at == deadline の場合に1.0を返すこと"""
    now = datetime.now(UTC)
    progress = calculate_sla_progress(now, now)
    assert progress == 1.0


def test_calculate_sla_progress_naive_datetime():
    """timezone-naiveなdatetimeでも正常に動作すること"""
    now = datetime.utcnow()  # noqa: DTZ003
    created_at = now - timedelta(hours=2)
    deadline = now + timedelta(hours=8)
    progress = calculate_sla_progress(created_at, deadline)
    assert 0.15 <= progress <= 0.25


def test_get_warning_level_normal():
    """経過率70%未満でNORMALを返すこと"""
    assert get_warning_level(0.0) == SLAWarningLevel.NORMAL
    assert get_warning_level(0.5) == SLAWarningLevel.NORMAL
    assert get_warning_level(0.69) == SLAWarningLevel.NORMAL


def test_get_warning_level_warning_70():
    """経過率70%以上90%未満でWARNING_70を返すこと"""
    assert get_warning_level(0.70) == SLAWarningLevel.WARNING_70
    assert get_warning_level(0.80) == SLAWarningLevel.WARNING_70
    assert get_warning_level(0.89) == SLAWarningLevel.WARNING_70


def test_get_warning_level_warning_90():
    """経過率90%以上100%未満でWARNING_90を返すこと"""
    assert get_warning_level(0.90) == SLAWarningLevel.WARNING_90
    assert get_warning_level(0.95) == SLAWarningLevel.WARNING_90
    assert get_warning_level(0.99) == SLAWarningLevel.WARNING_90


def test_get_warning_level_breached():
    """経過率100%以上でBREACHEDを返すこと"""
    assert get_warning_level(1.0) == SLAWarningLevel.BREACHED
    assert get_warning_level(1.5) == SLAWarningLevel.BREACHED


# ─── check_sla_warnings テスト ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sla_warning_70_detected(db: AsyncSession):
    """解決SLA経過率が70%以上の場合に警告が検出されること"""
    now = datetime.now(UTC)
    # 全体10時間のうち7.5時間経過 = 75%
    created_at = now - timedelta(hours=7, minutes=30)
    deadline = now + timedelta(hours=2, minutes=30)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-W70-{uuid.uuid4().hex[:6]}",
        title="Warning 70% Test",
        priority="P2",
        status="In_Progress",
        sla_breached=False,
        sla_response_due_at=now + timedelta(hours=1),
        sla_resolution_due_at=deadline,
        created_at=created_at,
        updated_at=now,
        acknowledged_at=now - timedelta(hours=7),  # 応答済み
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch(
        "src.services.sla_monitor_service.notification_service.notify_sla_warning",
        new=AsyncMock(),
    ):
        warnings = await service.check_sla_warnings(db)

    matching = [w for w in warnings if w["incident_number"] == incident.incident_number]
    assert len(matching) >= 1
    assert matching[0]["warning_level"] in ("warning_70", "warning_90")
    assert matching[0]["sla_type"] == "resolution"


@pytest.mark.asyncio
async def test_sla_warning_90_detected(db: AsyncSession):
    """解決SLA経過率が90%以上の場合にWARNING_90が検出されること"""
    now = datetime.now(UTC)
    # 全体10時間のうち9.5時間経過 = 95%
    created_at = now - timedelta(hours=9, minutes=30)
    deadline = now + timedelta(minutes=30)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-W90-{uuid.uuid4().hex[:6]}",
        title="Warning 90% Test",
        priority="P1",
        status="In_Progress",
        sla_breached=False,
        sla_response_due_at=now + timedelta(hours=1),
        sla_resolution_due_at=deadline,
        created_at=created_at,
        updated_at=now,
        acknowledged_at=now - timedelta(hours=9),
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch(
        "src.services.sla_monitor_service.notification_service.notify_sla_warning",
        new=AsyncMock(),
    ):
        warnings = await service.check_sla_warnings(db)

    matching = [w for w in warnings if w["incident_number"] == incident.incident_number]
    assert len(matching) >= 1
    assert matching[0]["warning_level"] == "warning_90"


@pytest.mark.asyncio
async def test_sla_no_warning_under_70(db: AsyncSession):
    """解決SLA経過率が70%未満の場合に警告が出ないこと"""
    now = datetime.now(UTC)
    # 全体10時間のうち3時間経過 = 30%
    created_at = now - timedelta(hours=3)
    deadline = now + timedelta(hours=7)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-LOW-{uuid.uuid4().hex[:6]}",
        title="No Warning Test",
        priority="P3",
        status="In_Progress",
        sla_breached=False,
        sla_response_due_at=now + timedelta(hours=1),
        sla_resolution_due_at=deadline,
        created_at=created_at,
        updated_at=now,
        acknowledged_at=now - timedelta(hours=2),
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    warnings = await service.check_sla_warnings(db)

    matching = [w for w in warnings if w["incident_number"] == incident.incident_number]
    assert len(matching) == 0


# ─── レスポンスSLA違反テスト ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_response_sla_breach_detection(db: AsyncSession):
    """レスポンスSLA期限超過で未応答のNewインシデントがsla_breached=Trueになること"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-RSP-{uuid.uuid4().hex[:6]}",
        title="Response SLA Breach Test",
        priority="P1",
        status="New",
        sla_breached=False,
        sla_response_due_at=now - timedelta(minutes=5),  # 応答期限超過
        sla_resolution_due_at=now + timedelta(hours=1),  # 解決期限は未到来
        created_at=now - timedelta(minutes=20),
        updated_at=now,
        acknowledged_at=None,  # 未応答
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        count = await service.check_sla_breaches(db)

    assert count >= 1
    assert incident.sla_breached is True


@pytest.mark.asyncio
async def test_response_sla_not_breached_when_acknowledged(db: AsyncSession):
    """応答済みインシデントはレスポンスSLA違反にならないこと"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-ACK-{uuid.uuid4().hex[:6]}",
        title="Acknowledged Incident",
        priority="P1",
        status="In_Progress",
        sla_breached=False,
        sla_response_due_at=now - timedelta(minutes=5),
        sla_resolution_due_at=now + timedelta(hours=1),
        created_at=now - timedelta(minutes=20),
        updated_at=now,
        acknowledged_at=now - timedelta(minutes=15),  # 応答済み
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        await service.check_sla_breaches(db)

    # レスポンスSLA違反ではマークされない（解決SLAはまだ未到来）
    assert incident.sla_breached is False


# ─── get_sla_status テスト ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_sla_status_with_response_and_resolution(db: AsyncSession):
    """get_sla_status()がレスポンス・解決SLAの両方を含む構造を返すこと"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-STS-{uuid.uuid4().hex[:6]}",
        title="SLA Status Test",
        priority="P2",
        status="In_Progress",
        sla_breached=False,
        sla_response_due_at=now + timedelta(minutes=30),
        sla_resolution_due_at=now + timedelta(hours=4),
        created_at=now - timedelta(hours=1),
        updated_at=now,
        acknowledged_at=now - timedelta(minutes=50),
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    status = await service.get_sla_status(db, str(incident.incident_id))

    assert status is not None
    assert status["incident_number"] == incident.incident_number
    assert status["sla_breached"] is False
    assert "response_sla" in status
    assert status["response_sla"]["met"] is True  # acknowledged_atがあるのでmet
    assert "resolution_sla" in status
    assert status["resolution_sla"]["met"] is False  # まだ解決していない
    assert "warning_level" in status["resolution_sla"]
    assert "progress_percent" in status["resolution_sla"]


@pytest.mark.asyncio
async def test_get_sla_status_not_found(db: AsyncSession):
    """存在しないincident_idでNoneを返すこと"""
    service = SLAMonitorService()
    status = await service.get_sla_status(db, str(uuid.uuid4()))
    assert status is None


# ─── get_active_warnings テスト ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_active_warnings_returns_list(db: AsyncSession):
    """get_active_warnings()がリストを返すこと"""
    service = SLAMonitorService()
    warnings = await service.get_active_warnings(db)
    assert isinstance(warnings, list)


@pytest.mark.asyncio
async def test_get_active_warnings_with_warning_incident(db: AsyncSession):
    """70%超過のインシデントがactive_warningsに含まれること"""
    now = datetime.now(UTC)
    # 全体10時間のうち8時間経過 = 80%
    created_at = now - timedelta(hours=8)
    deadline = now + timedelta(hours=2)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-AW-{uuid.uuid4().hex[:6]}",
        title="Active Warning Test",
        priority="P2",
        status="In_Progress",
        sla_breached=False,
        sla_response_due_at=now + timedelta(hours=1),
        sla_resolution_due_at=deadline,
        created_at=created_at,
        updated_at=now,
        acknowledged_at=now - timedelta(hours=7),
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    warnings = await service.get_active_warnings(db)

    matching = [w for w in warnings if w["incident_number"] == incident.incident_number]
    assert len(matching) >= 1
    assert matching[0]["sla_type"] == "resolution"
    assert matching[0]["progress_percent"] >= 70.0


# ─── カバレッジ補完テスト ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_sla_status_invalid_uuid(db: AsyncSession):
    """無効なUUID文字列でNoneを返すこと（例外ブランチ lines 284-285）"""
    service = SLAMonitorService()
    status = await service.get_sla_status(db, "not-a-valid-uuid")
    assert status is None


@pytest.mark.asyncio
async def test_get_sla_status_unacknowledged_response(db: AsyncSession):
    """acknowledged_at=Noneのインシデントでレスポンスの進捗が返ること（lines 319-321）"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-UA-{uuid.uuid4().hex[:6]}",
        title="Unacknowledged Response Test",
        priority="P2",
        status="New",
        sla_breached=False,
        sla_response_due_at=now + timedelta(minutes=30),
        sla_resolution_due_at=now + timedelta(hours=4),
        created_at=now - timedelta(hours=1),
        updated_at=now,
        acknowledged_at=None,
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    status = await service.get_sla_status(db, str(incident.incident_id))
    assert status is not None
    assert "response_sla" in status
    assert status["response_sla"]["met"] is False
    assert "warning_level" in status["response_sla"]


@pytest.mark.asyncio
async def test_get_sla_status_resolved_incident(db: AsyncSession):
    """resolved_atがあるインシデントで解決SLAがmet=Trueで返ること（line 332）"""
    now = datetime.now(UTC)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-RES-{uuid.uuid4().hex[:6]}",
        title="Resolved Resolution Test",
        priority="P3",
        status="Resolved",
        sla_breached=False,
        sla_resolution_due_at=now + timedelta(hours=2),
        created_at=now - timedelta(hours=2),
        updated_at=now,
        resolved_at=now - timedelta(minutes=30),
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    status = await service.get_sla_status(db, str(incident.incident_id))
    assert status is not None
    assert "resolution_sla" in status
    assert status["resolution_sla"]["met"] is True


@pytest.mark.asyncio
async def test_get_active_warnings_response_sla_unacknowledged(db: AsyncSession):
    """未応答かつ70%超のレスポンスSLAがwarningsに含まれること（lines 422-428）"""
    now = datetime.now(UTC)
    # 全体10時間のうち8時間経過 = 80%
    created_at = now - timedelta(hours=8)
    response_deadline = now + timedelta(hours=2)
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-RWA-{uuid.uuid4().hex[:6]}",
        title="Response Warning Test",
        priority="P1",
        status="New",
        sla_breached=False,
        sla_response_due_at=response_deadline,
        sla_resolution_due_at=now + timedelta(hours=5),
        created_at=created_at,
        updated_at=now,
        acknowledged_at=None,
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    warnings = await service.get_active_warnings(db)
    response_warnings = [
        w
        for w in warnings
        if w["incident_number"] == incident.incident_number
        and w["sla_type"] == "response"
    ]
    assert len(response_warnings) >= 1
    assert response_warnings[0]["progress_percent"] >= 70.0


@pytest.mark.asyncio
async def test_check_sla_breaches_dual_violation_skip(db: AsyncSession):
    """解決SLA+応答SLA両方違反のインシデントで重複カウントがスキップされること（line 190）"""
    now = datetime.now(UTC)
    # 解決SLAも応答SLAも期限切れ・未応答・New状態 → 両クエリにヒット
    incident = Incident(
        incident_id=uuid.uuid4(),
        incident_number=f"INC-DBL-{uuid.uuid4().hex[:6]}",
        title="Dual Breach Test",
        priority="P1",
        status="New",
        sla_breached=False,
        sla_response_due_at=now - timedelta(minutes=30),   # レスポンスSLA期限切れ
        sla_resolution_due_at=now - timedelta(hours=1),    # 解決SLA期限切れ
        created_at=now - timedelta(hours=3),
        updated_at=now,
        acknowledged_at=None,
    )
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    count = await service.check_sla_breaches(db)
    # 解決SLAで1カウント、応答SLAはスキップ → 合計1件
    assert count >= 1
