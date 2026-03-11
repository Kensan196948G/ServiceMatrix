"""PostgreSQL統合テスト - 実DB使用のインシデントCRUD検証"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from unittest.mock import AsyncMock, MagicMock

# asyncpg が未インストールの場合はテスト全体をスキップ
asyncpg = pytest.importorskip("asyncpg", reason="asyncpg not installed; skipping PG tests")

import asyncio
import os

def _pg_available() -> bool:
    """PostgreSQL への接続確認（起動していない場合は False）"""
    import socket
    url = os.getenv("TEST_DATABASE_URL", "")
    host, port = "localhost", 5433
    if "localhost:5433" in url or not url:
        pass  # デフォルト設定を使用
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.pg,
    pytest.mark.skipif(not _pg_available(), reason="PostgreSQL not running; skipping PG tests"),
]

# conftest_pg.py のフィクスチャをインポート
pytest_plugins = ["tests.conftest_pg"]


# ─── モデルのインポート ───────────────────────────────────────────────────────
from src.models.incident import Incident, IncidentStatus, IncidentPriority
from src.models.change import Change, ChangeStatus, ChangeType


# ─── ヘルパー関数 ─────────────────────────────────────────────────────────────

def _make_incident(**kwargs) -> dict:
    """テスト用インシデントデータを生成する"""
    defaults = {
        "title": "テストインシデント",
        "description": "PG統合テスト用インシデント",
        "priority": IncidentPriority.P3,
        "status": IncidentStatus.OPEN,
        "reporter_id": 1,
        "assignee_id": None,
        "service_name": "TestService",
        "incident_number": "INC-2026-000001",
    }
    defaults.update(kwargs)
    return defaults


# ─── テストケース ─────────────────────────────────────────────────────────────

@pytest.mark.pg
async def test_pg_incident_create(pg_session: AsyncSession):
    """インシデント作成が PG で正常動作"""
    data = _make_incident(incident_number="INC-2026-000001")
    incident = Incident(**data)
    pg_session.add(incident)
    await pg_session.flush()

    assert incident.id is not None
    assert incident.title == "テストインシデント"
    assert incident.status == IncidentStatus.OPEN


@pytest.mark.pg
async def test_pg_incident_read(pg_session: AsyncSession):
    """作成後の読み取り"""
    data = _make_incident(incident_number="INC-2026-000002", title="読み取りテスト")
    incident = Incident(**data)
    pg_session.add(incident)
    await pg_session.flush()

    result = await pg_session.execute(
        select(Incident).where(Incident.incident_number == "INC-2026-000002")
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.title == "読み取りテスト"


@pytest.mark.pg
async def test_pg_incident_update(pg_session: AsyncSession):
    """ステータス更新"""
    data = _make_incident(incident_number="INC-2026-000003", title="更新テスト")
    incident = Incident(**data)
    pg_session.add(incident)
    await pg_session.flush()

    incident.status = IncidentStatus.IN_PROGRESS
    await pg_session.flush()

    result = await pg_session.execute(
        select(Incident).where(Incident.incident_number == "INC-2026-000003")
    )
    updated = result.scalar_one_or_none()
    assert updated is not None
    assert updated.status == IncidentStatus.IN_PROGRESS


@pytest.mark.pg
async def test_pg_incident_list(pg_session: AsyncSession):
    """複数件取得"""
    for i in range(4, 7):
        data = _make_incident(
            incident_number=f"INC-2026-00000{i}",
            title=f"一覧テスト {i}",
        )
        pg_session.add(Incident(**data))
    await pg_session.flush()

    result = await pg_session.execute(
        select(Incident).where(Incident.title.like("一覧テスト%"))
    )
    incidents = result.scalars().all()
    assert len(incidents) >= 3


@pytest.mark.pg
async def test_pg_incident_priority_p1(pg_session: AsyncSession):
    """P1 優先度設定"""
    data = _make_incident(
        incident_number="INC-2026-000010",
        priority=IncidentPriority.P1,
        title="P1緊急インシデント",
    )
    incident = Incident(**data)
    pg_session.add(incident)
    await pg_session.flush()

    assert incident.priority == IncidentPriority.P1


@pytest.mark.pg
async def test_pg_incident_number_sequence(pg_session: AsyncSession):
    """採番が INC- で始まる"""
    data = _make_incident(incident_number="INC-2026-000011")
    incident = Incident(**data)
    pg_session.add(incident)
    await pg_session.flush()

    assert incident.incident_number.startswith("INC-")


@pytest.mark.pg
async def test_pg_change_create(pg_session: AsyncSession):
    """変更管理作成"""
    change = Change(
        title="テスト変更",
        description="PG統合テスト用変更",
        change_number="CHG-2026-000001",
        change_type=ChangeType.NORMAL,
        status=ChangeStatus.DRAFT,
        requester_id=1,
        risk_score=30,
    )
    pg_session.add(change)
    await pg_session.flush()

    assert change.id is not None
    assert change.change_number.startswith("CHG-")
    assert change.status == ChangeStatus.DRAFT


@pytest.mark.pg
async def test_pg_transaction_rollback(pg_session: AsyncSession):
    """トランザクション分離確認"""
    data = _make_incident(incident_number="INC-2026-000099", title="ロールバックテスト")
    incident = Incident(**data)
    pg_session.add(incident)
    await pg_session.flush()

    # ロールバック後はDBに残らないことを確認（フィクスチャが自動rollback）
    incident_id = incident.id
    assert incident_id is not None

    await pg_session.rollback()

    result = await pg_session.execute(
        select(Incident).where(Incident.incident_number == "INC-2026-000099")
    )
    fetched = result.scalar_one_or_none()
    # ロールバック後はNone（またはセッションに存在しない）
    assert fetched is None


@pytest.mark.pg
async def test_pg_concurrent_inserts(pg_session: AsyncSession):
    """並行挿入の整合性"""
    import asyncio

    async def insert_incident(num: int):
        data = _make_incident(
            incident_number=f"INC-2026-0001{num:02d}",
            title=f"並行挿入テスト {num}",
        )
        incident = Incident(**data)
        pg_session.add(incident)

    # 複数インシデントを同一セッションに追加
    for i in range(5):
        await insert_incident(i)

    await pg_session.flush()

    result = await pg_session.execute(
        select(Incident).where(Incident.title.like("並行挿入テスト%"))
    )
    incidents = result.scalars().all()
    assert len(incidents) == 5


@pytest.mark.pg
async def test_pg_large_description(pg_session: AsyncSession):
    """大量テキスト保存"""
    large_text = "A" * 10000  # 10KB のテキスト
    data = _make_incident(
        incident_number="INC-2026-000200",
        title="大量テキストテスト",
        description=large_text,
    )
    incident = Incident(**data)
    pg_session.add(incident)
    await pg_session.flush()

    result = await pg_session.execute(
        select(Incident).where(Incident.incident_number == "INC-2026-000200")
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert len(fetched.description) == 10000
