"""AIサービス ユニットテスト"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ai_service import AIService

pytestmark = pytest.mark.asyncio


async def test_summarize_mock_mode():
    svc = AIService()
    result = await svc.summarize_incident("Test Incident", "Description", [])
    assert "Test Incident" in result
    assert "[AI要約]" in result


async def test_summarize_mock_with_comments():
    svc = AIService()
    result = await svc.summarize_incident("Test", "Desc", ["c1", "c2"])
    assert "コメント2件" in result


async def test_summarize_no_description():
    svc = AIService()
    result = await svc.summarize_incident("Test", "", [])
    assert "[AI要約]" in result


async def test_generate_rca_mock_mode():
    svc = AIService()
    result = await svc.generate_rca_report("Problem A", ["svc1"], ["t1", "t2"])
    assert "root_cause" in result
    assert "recommendations" in result


async def test_generate_rca_empty_services():
    svc = AIService()
    result = await svc.generate_rca_report("Problem", [], [])
    assert isinstance(result, dict)
    assert "prevention_measures" in result


async def test_suggest_priority_critical():
    svc = AIService()
    result = await svc.suggest_incident_priority("critical: 全停止", "system down", None)
    assert result == "P1"


async def test_suggest_priority_high():
    svc = AIService()
    result = await svc.suggest_incident_priority("slow response 遅延", "slow", "api")
    assert result == "P2"


async def test_suggest_priority_normal():
    svc = AIService()
    result = await svc.suggest_incident_priority("Minor issue", "small bug", "svc")
    assert result == "P3"


async def test_summarize_api_mode_exception():
    svc = AIService()
    svc.provider = "openai"
    svc.api_key = "fake-key"
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection error"))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await svc.summarize_incident("T", "D", [])
    assert "[AI要約]" in result


async def test_rca_api_mode_exception():
    svc = AIService()
    svc.provider = "openai"
    svc.api_key = "fake-key"
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await svc.generate_rca_report("P", [], [])
    assert "root_cause" in result


async def test_priority_api_mode_exception():
    svc = AIService()
    svc.provider = "openai"
    svc.api_key = "fake-key"
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await svc.suggest_incident_priority("T", "D", None)
    assert result == "P3"
