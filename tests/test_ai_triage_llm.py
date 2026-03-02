"""LLMプロバイダー抽象化テスト - OpenAI/Azure/Ollama切り替え対応"""
import sys
from unittest.mock import AsyncMock, patch

import pytest

from src.services.ai_triage_service import (
    AITriageResult,
    AITriageService,
    KeywordTriageProvider,
    OpenAITriageProvider,
    get_triage_provider,
)


@pytest.mark.asyncio
async def test_get_triage_provider_default_returns_keyword():
    """設定なし → KeywordTriageProvider を返す"""
    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "keyword"
        mock_settings.openai_api_key = ""
        mock_settings.openai_api_base = ""
        mock_settings.llm_model = "gpt-4o-mini"
        provider = get_triage_provider()
    assert isinstance(provider, KeywordTriageProvider)


@pytest.mark.asyncio
async def test_get_triage_provider_openai_with_key():
    """openai + api_key設定 → OpenAITriageProvider を返す"""
    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "sk-test-key"  # noqa: S105
        mock_settings.openai_api_base = ""
        mock_settings.llm_model = "gpt-4o-mini"
        provider = get_triage_provider()
    assert isinstance(provider, OpenAITriageProvider)
    assert provider.api_key == "sk-test-key"  # noqa: S105


@pytest.mark.asyncio
async def test_openai_provider_fallback_without_package():
    """openaiパッケージ未インストール時 → KeywordProviderにフォールバック"""
    provider = OpenAITriageProvider(api_key="sk-test", model="gpt-4o-mini")  # noqa: S106

    # openai モジュールを一時的に import 不可にする
    with patch.dict(sys.modules, {"openai": None}):
        result = await provider.analyze("production down", "critical outage")

    assert isinstance(result, AITriageResult)
    assert result.priority == "Critical"


@pytest.mark.asyncio
async def test_triage_service_uses_provider(monkeypatch):
    """AITriageService.triage() がプロバイダーを経由することを確認"""
    mock_result = AITriageResult(
        priority="High",
        category="Network",
        confidence=0.85,
        reasoning="Mocked LLM response",
    )
    mock_provider = AsyncMock()
    mock_provider.analyze = AsyncMock(return_value=mock_result)

    monkeypatch.setattr(
        "src.services.ai_triage_service.get_triage_provider",
        lambda: mock_provider,
    )

    svc = AITriageService()
    result = await svc.triage("network connectivity issue", None)

    mock_provider.analyze.assert_called_once_with("network connectivity issue", None)
    assert result.priority == "High"
    assert result.category == "Network"


@pytest.mark.asyncio
async def test_keyword_provider_still_works():
    """KeywordTriageProvider が既存テストと同じ結果を返すことを確認"""
    provider = KeywordTriageProvider()

    result_critical = await provider.analyze("production down", None)
    assert result_critical.priority == "Critical"
    assert result_critical.confidence >= 0.8

    result_security = await provider.analyze("unauthorized access detected", "security breach")
    assert result_security.category == "Security"

    result_medium = await provider.analyze("service update notification", "scheduled maintenance")
    assert result_medium.priority == "Medium"
