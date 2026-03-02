"""AIトリアージサービステスト - キーワードベース優先度・カテゴリ判定"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.ai_triage_service import AITriageResult, AITriageService


@pytest.fixture
def svc():
    return AITriageService()


# ─── 優先度判定テスト ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_triage_critical_priority(svc):
    """'production down' → Critical 判定"""
    result = await svc.triage("production down", None)
    assert result.priority == "Critical"
    assert result.confidence >= 0.8


@pytest.mark.asyncio
async def test_triage_high_priority(svc):
    """'database error' → High 判定"""
    result = await svc.triage("database error", None)
    assert result.priority == "High"
    assert result.confidence >= 0.7


@pytest.mark.asyncio
async def test_triage_medium_priority(svc):
    """一般的なテキスト → Medium 判定"""
    result = await svc.triage("service update notification", "The system will be updated")
    assert result.priority == "Medium"


@pytest.mark.asyncio
async def test_triage_low_priority(svc):
    """情報系キーワード → Low 判定"""
    result = await svc.triage("inquiry about billing", "I have a question about my invoice")
    assert result.priority == "Low"


# ─── カテゴリ判定テスト ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_triage_security_category(svc):
    """セキュリティキーワード → Security カテゴリ"""
    result = await svc.triage("unauthorized access detected", "security breach in login module")
    assert result.category == "Security"


@pytest.mark.asyncio
async def test_triage_network_category(svc):
    """ネットワークキーワード → Network カテゴリ"""
    result = await svc.triage("network connectivity issue", "dns resolution failing")
    assert result.category == "Network"


@pytest.mark.asyncio
async def test_triage_db_category(svc):
    """DBキーワード → Database カテゴリ"""
    result = await svc.triage("slow database query", "sql query taking 30 seconds")
    assert result.category == "Database"


# ─── 統合テスト ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_triage_to_incident(svc):
    """apply_triage_to_incident() がDBからインシデントを取得してトリアージを保存する"""
    incident_id = str(uuid.uuid4())
    mock_incident = MagicMock()
    mock_incident.incident_id = incident_id
    mock_incident.title = "production outage"
    mock_incident.description = "critical system down"
    mock_incident.ai_triage_notes = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_incident

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()

    result = await svc.apply_triage_to_incident(mock_db, incident_id)

    assert result.priority == "Critical"
    assert isinstance(result.confidence, float)
    assert mock_incident.ai_triage_notes is not None
    assert "Priority=Critical" in mock_incident.ai_triage_notes
    mock_db.flush.assert_called_once()
