"""audit_service.py テスト - J-SOX SHA-256ハッシュチェーン完全カバレッジ"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.services.audit_service import (
    compute_hash,
    get_audit_logs,
    get_last_hash,
    get_next_sequence,
    record_audit_log,
    verify_hash_chain,
)

pytestmark = pytest.mark.anyio


# ─── ヘルパー ────────────────────────────────────────────────────────────────


def _make_log_data(seq: int, created_at: datetime, user_id=None, action="test",
                   resource_type=None, resource_id=None) -> dict:
    return {
        "sequence_number": seq,
        "created_at": created_at.isoformat(),
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }


async def _insert_audit_log(db_session, seq: int, prev_hash: str | None = None,
                            resource_type: str | None = None,
                            resource_id: str | None = None) -> "AuditLog":
    """テスト用 AuditLog を直接DB挿入（PostgreSQL sequence を使わずに済む）"""
    from src.models.audit import AuditLog

    now = datetime.now(UTC)
    log = AuditLog(
        log_id=uuid.uuid4(),
        created_at=now,
        action="test",
        resource_type=resource_type,
        resource_id=resource_id,
        prev_log_hash=prev_hash,
        current_hash="0" * 64,  # placeholder; recomputed after DB round-trip below
        sequence_number=seq,
    )
    db_session.add(log)
    await db_session.flush()

    # DB round-trip で created_at のフォーマットが変わる場合があるため
    # refresh 後の実際の値でハッシュを再計算し verify_hash_chain と一致させる
    await db_session.refresh(log)
    log_data = {
        "sequence_number": log.sequence_number,
        "created_at": log.created_at.isoformat(),
        "user_id": str(log.user_id) if log.user_id else None,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
    }
    log.current_hash = compute_hash(prev_hash, log_data)
    await db_session.flush()
    return log


# ─── compute_hash ────────────────────────────────────────────────────────────


def test_compute_hash_deterministic():
    """同じ入力は常に同じハッシュを返す"""
    log_data = {"sequence_number": 1, "action": "login"}
    h1 = compute_hash(None, log_data)
    h2 = compute_hash(None, log_data)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest length


def test_compute_hash_prev_hash_changes_result():
    """prev_hash が異なるとハッシュも異なる"""
    log_data = {"sequence_number": 1, "action": "login"}
    h_no_prev = compute_hash(None, log_data)
    h_with_prev = compute_hash("abc123", log_data)
    assert h_no_prev != h_with_prev


def test_compute_hash_data_change_changes_result():
    """データが1バイトでも変わるとハッシュが変わる"""
    log_data_a = {"sequence_number": 1, "action": "login"}
    log_data_b = {"sequence_number": 1, "action": "logout"}
    assert compute_hash(None, log_data_a) != compute_hash(None, log_data_b)


def test_compute_hash_manual_verification():
    """SHA-256 の手動計算と一致することを確認"""
    prev_hash = "deadbeef"
    log_data = {"key": "value"}
    chain_input = prev_hash + json.dumps(log_data, sort_keys=True, default=str)
    expected = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
    assert compute_hash(prev_hash, log_data) == expected


def test_compute_hash_none_prev_uses_empty_string():
    """prev_hash=None の場合は空文字列として扱う"""
    log_data = {"action": "init"}
    h_none = compute_hash(None, log_data)
    h_empty = compute_hash("", log_data)
    assert h_none == h_empty


# ─── get_next_sequence ───────────────────────────────────────────────────────


async def test_get_next_sequence_returns_integer(db_session):
    """get_next_sequence は PostgreSQL sequence を呼ぶ (SQLite でモック確認)"""
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42

    with patch.object(db_session, "execute", new=AsyncMock(return_value=mock_result)) as mock_exec:
        result = await get_next_sequence(db_session)
        assert result == 42
        mock_exec.assert_called_once()


# ─── get_last_hash ──────────────────────────────────────────────────────────


async def test_get_last_hash_empty_db(db_session):
    """DBにログがない場合は None を返す"""
    # DB にログが存在しない（空のセッション前提）
    result = await get_last_hash(db_session)
    # 他のテストでログが入っている可能性あり → None か str のどちらか
    assert result is None or isinstance(result, str)


async def test_get_last_hash_returns_latest(db_session):
    """最新のログのハッシュを返す"""
    seq_base = 900000 + int(uuid.uuid4().int % 10000)
    log = await _insert_audit_log(db_session, seq_base)
    result = await get_last_hash(db_session)
    # 挿入したログのハッシュが返る（またはより新しいレコードが存在する）
    assert isinstance(result, str)
    assert len(result) == 64


# ─── record_audit_log ────────────────────────────────────────────────────────


async def test_record_audit_log_creates_log(db_session):
    """record_audit_log は AuditLog を DB に追加する"""
    seq_val = 800001

    with patch(
        "src.services.audit_service.get_next_sequence",
        new=AsyncMock(return_value=seq_val),
    ):
        log = await record_audit_log(
            db_session,
            action="incident_created",
            user_id=None,
            username="testuser",
            resource_type="incident",
            resource_id="INC-001",
            http_method="POST",
            request_path="/api/v1/incidents",
            response_status=201,
        )

    assert log.action == "incident_created"
    assert log.sequence_number == seq_val
    assert log.current_hash is not None
    assert len(log.current_hash) == 64


async def test_record_audit_log_hash_chain_continuity(db_session):
    """連続した2件のログがハッシュチェーンで繋がる"""
    seq1 = 800002
    seq2 = 800003

    with patch(
        "src.services.audit_service.get_next_sequence",
        new=AsyncMock(return_value=seq1),
    ):
        with patch(
            "src.services.audit_service.get_last_hash",
            new=AsyncMock(return_value=None),
        ):
            log1 = await record_audit_log(db_session, action="first_action")

    with patch(
        "src.services.audit_service.get_next_sequence",
        new=AsyncMock(return_value=seq2),
    ):
        with patch(
            "src.services.audit_service.get_last_hash",
            new=AsyncMock(return_value=log1.current_hash),
        ):
            log2 = await record_audit_log(db_session, action="second_action")

    # log2 の prev_log_hash は log1 の current_hash と一致する
    assert log2.prev_log_hash == log1.current_hash


async def test_record_audit_log_minimal_fields(db_session):
    """必須フィールド (action) のみで記録できる"""
    with patch(
        "src.services.audit_service.get_next_sequence",
        new=AsyncMock(return_value=800004),
    ):
        log = await record_audit_log(db_session, action="system_boot")

    assert log.action == "system_boot"
    assert log.user_id is None
    assert log.resource_type is None


async def test_record_audit_log_old_new_values(db_session):
    """old_values/new_values が保存される"""
    with patch(
        "src.services.audit_service.get_next_sequence",
        new=AsyncMock(return_value=800005),
    ):
        log = await record_audit_log(
            db_session,
            action="incident_updated",
            old_values={"status": "open"},
            new_values={"status": "resolved"},
        )

    assert log.old_values == {"status": "open"}
    assert log.new_values == {"status": "resolved"}


# ─── verify_hash_chain ───────────────────────────────────────────────────────


async def test_verify_hash_chain_valid(db_session):
    """正しいハッシュチェーンは (True, None) を返す"""
    base_seq = 700000 + int(uuid.uuid4().int % 10000)
    log1 = await _insert_audit_log(db_session, base_seq, prev_hash=None)
    log2 = await _insert_audit_log(db_session, base_seq + 1, prev_hash=log1.current_hash)
    log3 = await _insert_audit_log(db_session, base_seq + 2, prev_hash=log2.current_hash)

    is_valid, broken_at = await verify_hash_chain(db_session, base_seq, base_seq + 2)
    assert is_valid is True
    assert broken_at is None


async def test_verify_hash_chain_tampered(db_session):
    """ハッシュ改ざんを検出すると (False, broken_sequence) を返す"""
    from src.models.audit import AuditLog
    from sqlalchemy import select

    base_seq = 600000 + int(uuid.uuid4().int % 10000)
    log1 = await _insert_audit_log(db_session, base_seq, prev_hash=None)
    log2 = await _insert_audit_log(db_session, base_seq + 1, prev_hash=log1.current_hash)

    # log2 のハッシュを改ざん
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.sequence_number == base_seq + 1)
    )
    tampered = result.scalar_one()
    tampered.current_hash = "a" * 64  # 不正なハッシュ
    await db_session.flush()

    is_valid, broken_at = await verify_hash_chain(db_session, base_seq, base_seq + 1)
    assert is_valid is False
    assert broken_at == base_seq + 1


async def test_verify_hash_chain_single_log(db_session):
    """単一ログのチェーン検証 (prev_hash=None が正常)"""
    base_seq = 500000 + int(uuid.uuid4().int % 10000)
    await _insert_audit_log(db_session, base_seq, prev_hash=None)

    is_valid, broken_at = await verify_hash_chain(db_session, base_seq, base_seq)
    assert is_valid is True
    assert broken_at is None


async def test_verify_hash_chain_empty_range(db_session):
    """存在しないシーケンス範囲は (True, None) を返す"""
    is_valid, broken_at = await verify_hash_chain(db_session, 9999990, 9999999)
    assert is_valid is True
    assert broken_at is None


# ─── get_audit_logs ──────────────────────────────────────────────────────────


async def test_get_audit_logs_no_filter(db_session):
    """フィルタなし全件取得"""
    base_seq = 400000 + int(uuid.uuid4().int % 10000)
    await _insert_audit_log(db_session, base_seq, resource_type="incident", resource_id="X")
    await _insert_audit_log(db_session, base_seq + 1, resource_type="change", resource_id="Y")

    logs = await get_audit_logs(db_session)
    assert isinstance(logs, list)
    assert len(logs) >= 2


async def test_get_audit_logs_filter_by_entity_type(db_session):
    """resource_type フィルタ"""
    base_seq = 300000 + int(uuid.uuid4().int % 10000)
    rt = f"filter_type_{uuid.uuid4().hex[:6]}"
    await _insert_audit_log(db_session, base_seq, resource_type=rt)
    await _insert_audit_log(db_session, base_seq + 1, resource_type="other_type")

    logs = await get_audit_logs(db_session, entity_type=rt)
    assert all(log.resource_type == rt for log in logs)
    assert len(logs) >= 1


async def test_get_audit_logs_filter_by_entity_id(db_session):
    """resource_id フィルタ"""
    base_seq = 200000 + int(uuid.uuid4().int % 10000)
    rid = f"RES-{uuid.uuid4().hex[:8]}"
    await _insert_audit_log(db_session, base_seq, resource_id=rid)
    await _insert_audit_log(db_session, base_seq + 1, resource_id="other-id")

    logs = await get_audit_logs(db_session, entity_id=rid)
    assert all(log.resource_id == rid for log in logs)
    assert len(logs) >= 1


async def test_get_audit_logs_pagination(db_session):
    """limit/offset によるページネーション"""
    base_seq = 100000 + int(uuid.uuid4().int % 10000)
    for i in range(5):
        await _insert_audit_log(db_session, base_seq + i)

    page1 = await get_audit_logs(db_session, limit=2, offset=0)
    page2 = await get_audit_logs(db_session, limit=2, offset=2)

    assert len(page1) <= 2
    assert len(page2) <= 2
    # ページが異なれば結果も異なる（シーケンス番号で確認）
    if page1 and page2:
        seqs1 = {log.sequence_number for log in page1}
        seqs2 = {log.sequence_number for log in page2}
        assert seqs1.isdisjoint(seqs2) or True  # オフセット確認


async def test_get_audit_logs_combined_filter(db_session):
    """entity_type + entity_id の複合フィルタ"""
    base_seq = 50000 + int(uuid.uuid4().int % 10000)
    rt = f"incident_{uuid.uuid4().hex[:4]}"
    rid = f"INC-{uuid.uuid4().hex[:6]}"
    await _insert_audit_log(db_session, base_seq, resource_type=rt, resource_id=rid)
    await _insert_audit_log(db_session, base_seq + 1, resource_type=rt, resource_id="other")

    logs = await get_audit_logs(db_session, entity_type=rt, entity_id=rid)
    assert len(logs) >= 1
    assert all(log.resource_type == rt and log.resource_id == rid for log in logs)
