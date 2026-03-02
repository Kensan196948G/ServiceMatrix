"""SLA自動監視バックグラウンドエンジン テスト"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.models.incident import Incident
from src.services.sla_monitor_service import SLAMonitorService, sla_monitor

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
    incident = _make_incident(priority="P1", status="In_Progress", sla_resolution_due_at=past_deadline)
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
    incident = _make_incident(priority="P2", status="In_Progress", sla_resolution_due_at=future_deadline)
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
    incident = _make_incident(priority="P4", status="New", sla_resolution_due_at=future, sla_breached=False)
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
    incident = _make_incident(priority="P1", status="Acknowledged", sla_resolution_due_at=past_deadline)
    db.add(incident)
    await db.flush()

    service = SLAMonitorService()
    with patch("src.services.sla_monitor_service.audit_service.record_audit_log", new=AsyncMock()):
        await service.check_sla_breaches(db)

    assert incident.sla_breached is True
    assert incident.sla_breached_at is not None
    assert isinstance(incident.sla_breached_at, datetime)
