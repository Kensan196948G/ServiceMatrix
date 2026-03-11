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


# ─── Anthropic プロバイダーブランチ ────────────────────────────────────────────


async def test_summarize_anthropic_mode():
    """AIService: anthropic プロバイダーで要約を生成"""
    import sys

    svc = AIService()
    svc.provider = "anthropic"
    svc.api_key = "test-key"
    svc.model = "claude-3-5-haiku-20241022"

    mock_content = MagicMock()
    mock_content.text = "テスト要約テキスト"
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.AsyncAnthropic = MagicMock(return_value=mock_client)

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
        result = await svc.summarize_incident("テストインシデント", "説明文", ["コメント1"])

    assert result == "テスト要約テキスト"


async def test_rca_anthropic_mode():
    """AIService: anthropic プロバイダーで RCA レポートを生成（JSON解析成功）"""
    import sys

    svc = AIService()
    svc.provider = "anthropic"
    svc.api_key = "test-key"
    svc.model = "claude-3-5-haiku-20241022"

    mock_content = MagicMock()
    mock_content.text = '{"root_cause": "DB過負荷", "contributing_factors": ["high load"], "recommendations": ["スケールアップ"], "prevention_measures": ["監視強化"]}'
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.AsyncAnthropic = MagicMock(return_value=mock_client)

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
        result = await svc.generate_rca_report("DB問題", ["svc-a"], ["10:00 障害発生"])

    assert result["root_cause"] == "DB過負荷"
    assert "recommendations" in result


async def test_priority_anthropic_mode():
    """AIService: anthropic プロバイダーで優先度提案"""
    import sys

    svc = AIService()
    svc.provider = "anthropic"
    svc.api_key = "test-key"

    mock_content = MagicMock()
    mock_content.text = "P2"
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.AsyncAnthropic = MagicMock(return_value=mock_client)

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
        result = await svc.suggest_incident_priority("遅延発生", "APIが低速", "api-svc")

    assert result == "P2"


async def test_anthropic_text_import_error():
    """AIService._anthropic_text: anthropic未インストール → None を返す"""
    import sys

    svc = AIService()
    svc.provider = "anthropic"
    svc.api_key = "test-key"

    with patch.dict(sys.modules, {"anthropic": None}):
        result = await svc._anthropic_text("test prompt", 100)

    assert result is None


async def test_anthropic_model_fallback():
    """AIService._anthropic_text: claude-以外のモデル名 → claude-3-5-haiku にフォールバック"""
    import sys

    svc = AIService()
    svc.provider = "anthropic"
    svc.api_key = "test-key"
    svc.model = "gpt-4o-mini"  # claude-で始まらない → フォールバック

    mock_content = MagicMock()
    mock_content.text = "テスト結果"
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.AsyncAnthropic = MagicMock(return_value=mock_client)

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
        result = await svc._anthropic_text("prompt", 100)

    # claude-3-5-haiku-20241022 でAPIが呼ばれたことを確認
    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == "claude-3-5-haiku-20241022"
    assert result == "テスト結果"
