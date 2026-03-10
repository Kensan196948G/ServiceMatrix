"""監査ログAPI 直接呼び出しカバレッジテスト

対象: src/api/v1/audit.py
目的: async関数ボディ（ASGI経由で未追跡）のパスをカバー
カバー対象行: 39, 59, 75-80, 109, 111, 113, 116-133, 150-184
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


# ─── ヘルパー ──────────────────────────────────────────────────────────────


def _make_user():
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = UserRole.SYSTEM_ADMIN
    return u


def _make_audit_log_mock(
    *,
    seq: int = 1,
    action: str = "CREATE",
    resource_type: str | None = "incident",
    resource_id: str | None = "INC-001",
    username: str | None = "admin",
    user_id: uuid.UUID | None = None,
    new_values: dict | None = None,
):
    """AuditLog モックオブジェクト生成"""
    log = MagicMock()
    log.log_id = uuid.uuid4()
    log.sequence_number = seq
    log.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    log.action = action
    log.resource_type = resource_type
    log.resource_id = resource_id
    log.username = username
    log.user_id = user_id
    log.new_values = new_values
    log.prev_log_hash = None
    log.current_hash = "abc123"
    return log


# ─── list_audit_logs テスト（line 39） ─────────────────────────────────────


async def test_list_audit_logs_direct_with_data():
    """list_audit_logs: ログあり → AuditLogResponse.model_validate 実行 (line 39)"""
    from src.api.v1.audit import list_audit_logs
    from src.schemas.audit import AuditLogResponse

    mock_logs = [
        _make_audit_log_mock(seq=1, action="CREATE"),
        _make_audit_log_mock(seq=2, action="UPDATE"),
    ]

    with patch(
        "src.api.v1.audit.get_audit_logs",
        new=AsyncMock(return_value=mock_logs),
    ):
        db = MagicMock()
        user = _make_user()
        result = await list_audit_logs(
            db=db,
            current_user=user,
            entity_type=None,
            entity_id=None,
            limit=50,
            offset=0,
        )

    assert len(result) == 2
    assert all(isinstance(r, AuditLogResponse) for r in result)


async def test_list_audit_logs_direct_empty():
    """list_audit_logs: ログなし → 空リスト返却"""
    from src.api.v1.audit import list_audit_logs

    with patch("src.api.v1.audit.get_audit_logs", new=AsyncMock(return_value=[])):
        db = MagicMock()
        user = _make_user()
        result = await list_audit_logs(
            db=db, current_user=user, entity_type="incident", entity_id="INC-001",
            limit=50, offset=0,
        )

    assert result == []


# ─── get_entity_audit_logs テスト（line 59） ──────────────────────────────


async def test_get_entity_audit_logs_direct():
    """get_entity_audit_logs: エンティティ別ログ取得 (line 59)"""
    from src.api.v1.audit import get_entity_audit_logs
    from src.schemas.audit import AuditLogResponse

    mock_logs = [_make_audit_log_mock(seq=10, resource_type="change", resource_id="CHG-001")]

    with patch("src.api.v1.audit.get_audit_logs", new=AsyncMock(return_value=mock_logs)):
        db = MagicMock()
        user = _make_user()
        result = await get_entity_audit_logs(
            entity_type="change",
            entity_id="CHG-001",
            db=db,
            current_user=user,
            limit=50,
            offset=0,
        )

    assert len(result) == 1
    assert isinstance(result[0], AuditLogResponse)


# ─── verify_audit_chain テスト（lines 75-80） ─────────────────────────────


async def test_verify_audit_chain_invalid_direct():
    """verify_audit_chain: is_valid=False → エラーメッセージ生成 (lines 75-80)"""
    from src.api.v1.audit import verify_audit_chain

    with patch(
        "src.api.v1.audit.verify_hash_chain",
        new=AsyncMock(return_value=(False, 42)),
    ):
        db = MagicMock()
        user = _make_user()
        result = await verify_audit_chain(
            db=db, current_user=user, start_seq=1, end_seq=100
        )

    assert result.is_valid is False
    assert result.first_invalid_sequence == 42
    assert "42" in result.message
    assert "不整合" in result.message


async def test_verify_audit_chain_valid_direct():
    """verify_audit_chain: is_valid=True → 正常メッセージ (lines 72-74)"""
    from src.api.v1.audit import verify_audit_chain

    with patch(
        "src.api.v1.audit.verify_hash_chain",
        new=AsyncMock(return_value=(True, None)),
    ):
        db = MagicMock()
        user = _make_user()
        result = await verify_audit_chain(
            db=db, current_user=user, start_seq=1, end_seq=50
        )

    assert result.is_valid is True
    assert result.checked_count == 50
    assert "正常" in result.message


# ─── export_audit_logs テスト（lines 109, 111, 113, 116-133） ─────────────


def _make_db_for_export(logs):
    """export_audit_logs 用 DB モック"""
    db = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = logs
    result = MagicMock()
    result.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result)
    return db


async def test_export_audit_logs_with_data_direct():
    """export_audit_logs: ログあり → CSV行書き込み (lines 116-133)"""
    from src.api.v1.audit import export_audit_logs

    logs = [
        _make_audit_log_mock(seq=1, action="CREATE", resource_type="incident",
                              resource_id="INC-001", username="admin"),
        _make_audit_log_mock(seq=2, action="UPDATE", resource_type="change",
                              resource_id="CHG-001", user_id=uuid.uuid4(), username=None,
                              new_values={"status": "Approved"}),
    ]
    db = _make_db_for_export(logs)
    user = _make_user()

    response = await export_audit_logs(
        db=db, current_user=user,
        entity_type=None, entity_id=None,
        date_from=None, date_to=None,
        limit=5000,
    )

    assert response.media_type == "text/csv"
    content = response.body.decode("utf-8")
    assert "timestamp" in content
    assert "CREATE" in content
    assert "UPDATE" in content
    assert "incident" in content


async def test_export_audit_logs_with_entity_type_filter():
    """export_audit_logs: entity_type フィルタ適用 (line 109)"""
    from src.api.v1.audit import export_audit_logs

    db = _make_db_for_export([])
    user = _make_user()

    # entity_type が渡された場合 → where 句追加（line 109）
    response = await export_audit_logs(
        db=db, current_user=user,
        entity_type="incident", entity_id=None,
        date_from=None, date_to=None,
        limit=5000,
    )

    assert response.media_type == "text/csv"
    # where句が追加されてもクラッシュしない
    db.execute.assert_called_once()


async def test_export_audit_logs_with_entity_id_filter():
    """export_audit_logs: entity_id フィルタ適用 (line 111)"""
    from src.api.v1.audit import export_audit_logs

    db = _make_db_for_export([])
    user = _make_user()

    response = await export_audit_logs(
        db=db, current_user=user,
        entity_type="incident", entity_id="INC-001",
        date_from=None, date_to=None,
        limit=5000,
    )

    assert response.media_type == "text/csv"


async def test_export_audit_logs_with_date_filters():
    """export_audit_logs: date_from/date_to フィルタ (lines 111, 113)"""
    from src.api.v1.audit import export_audit_logs

    db = _make_db_for_export([])
    user = _make_user()

    response = await export_audit_logs(
        db=db, current_user=user,
        entity_type=None, entity_id=None,
        date_from=datetime(2026, 1, 1, tzinfo=UTC),
        date_to=datetime(2026, 1, 31, tzinfo=UTC),
        limit=5000,
    )

    assert response.media_type == "text/csv"


async def test_export_audit_logs_no_username():
    """export_audit_logs: username=None, user_id あり → user_id を user 列に出力"""
    from src.api.v1.audit import export_audit_logs

    uid = uuid.uuid4()
    log = _make_audit_log_mock(seq=1, username=None, user_id=uid)
    db = _make_db_for_export([log])
    user = _make_user()

    response = await export_audit_logs(
        db=db, current_user=user,
        entity_type=None, entity_id=None,
        date_from=None, date_to=None,
        limit=5000,
    )

    content = response.body.decode("utf-8")
    assert str(uid) in content


async def test_export_audit_logs_empty():
    """export_audit_logs: ログなし → ヘッダーのみのCSV"""
    from src.api.v1.audit import export_audit_logs

    db = _make_db_for_export([])
    user = _make_user()

    response = await export_audit_logs(
        db=db, current_user=user,
        entity_type=None, entity_id=None,
        date_from=None, date_to=None,
        limit=5000,
    )

    content = response.body.decode("utf-8")
    # ヘッダー行のみ
    assert "timestamp" in content
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1  # ヘッダーのみ


# ─── get_audit_stats テスト（lines 150-184） ──────────────────────────────


def _make_stats_db(
    *,
    total: int = 5,
    unique_users: int = 2,
    by_action: list | None = None,
    by_resource: list | None = None,
    recent_logs: list | None = None,
):
    """get_audit_stats 用 DB モック（5回 execute）"""
    if by_action is None:
        by_action = []
    if by_resource is None:
        by_resource = []
    if recent_logs is None:
        recent_logs = []

    # result 1: total count
    r1 = MagicMock()
    r1.scalar_one.return_value = total

    # result 2: unique users
    r2 = MagicMock()
    r2.scalar_one.return_value = unique_users

    # result 3: by_action rows
    r3 = MagicMock()
    r3.__iter__ = MagicMock(return_value=iter(by_action))

    # result 4: by_resource rows
    r4 = MagicMock()
    r4.__iter__ = MagicMock(return_value=iter(by_resource))

    # result 5: recent logs
    r5_scalars = MagicMock()
    r5_scalars.all.return_value = recent_logs
    r5 = MagicMock()
    r5.scalars.return_value = r5_scalars

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[r1, r2, r3, r4, r5])
    return db


async def test_get_audit_stats_direct():
    """get_audit_stats: 統計データ取得 (lines 150-184)"""
    from src.api.v1.audit import get_audit_stats

    # by_action rows mock
    action_row = MagicMock()
    action_row.action = "CREATE"
    action_row.cnt = 3

    # by_resource rows mock
    resource_row = MagicMock()
    resource_row.resource_type = "incident"
    resource_row.cnt = 5

    # recent log mock
    recent = _make_audit_log_mock(seq=1, action="CREATE",
                                  resource_type="incident", resource_id="INC-001",
                                  username="admin")

    db = _make_stats_db(
        total=10,
        unique_users=3,
        by_action=[action_row],
        by_resource=[resource_row],
        recent_logs=[recent],
    )
    user = _make_user()

    result = await get_audit_stats(db=db, current_user=user)

    assert result["total_operations"] == 10
    assert result["unique_users"] == 3
    assert result["by_action"]["CREATE"] == 3
    assert result["by_resource"]["incident"] == 5
    assert len(result["recent_activity"]) == 1
    assert result["recent_activity"][0]["action"] == "CREATE"


async def test_get_audit_stats_empty_direct():
    """get_audit_stats: データなし"""
    from src.api.v1.audit import get_audit_stats

    db = _make_stats_db(total=0, unique_users=0)
    user = _make_user()

    result = await get_audit_stats(db=db, current_user=user)

    assert result["total_operations"] == 0
    assert result["unique_users"] == 0
    assert result["by_action"] == {}
    assert result["by_resource"] == {}
    assert result["recent_activity"] == []


async def test_get_audit_stats_recent_no_username():
    """get_audit_stats: username=None の最近ログ → user=None"""
    from src.api.v1.audit import get_audit_stats

    recent = _make_audit_log_mock(seq=1, username=None, user_id=None)

    db = _make_stats_db(recent_logs=[recent])
    user = _make_user()

    result = await get_audit_stats(db=db, current_user=user)

    assert result["recent_activity"][0]["user"] is None
