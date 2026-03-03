"""AIトリアージAPIエンドポイント直接呼び出しテスト

エンドポイント関数を直接awaitしてカバレッジを取得するパターンを使用。
"""

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.ai_triage import (
    analyze_text,
    batch_triage,
    get_provider_info,
    triage_incident,
)
from src.models.user import User, UserRole
from src.schemas.ai_triage import (
    BatchTriageRequest,
    IncidentTriageRequest,
    TriageRequest,
)
from src.services.ai_triage_service import (
    AITriageResult,
    AITriageService,
    ClaudeTriageProvider,
    KeywordTriageProvider,
    OpenAITriageProvider,
    get_triage_provider,
)

pytestmark = pytest.mark.asyncio


def _make_user(**overrides):
    defaults = {
        "user_id": uuid.uuid4(),
        "username": "testadmin",
        "email": "admin@test.com",
        "role": UserRole.SYSTEM_ADMIN,
        "is_active": True,
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


# ─── POST /ai-triage/analyze テスト ────────────────────────────────────────────


async def test_analyze_text_success():
    """手動トリアージ: キーワードマッチでCritical判定"""
    user = _make_user()
    req = TriageRequest(title="production down", description="critical outage")

    result = await analyze_text(data=req, current_user=user)

    assert result.priority == "Critical"
    assert result.confidence >= 0.8
    assert result.provider == "keyword"


async def test_analyze_text_medium_default():
    """手動トリアージ: キーワード不一致でMedium判定"""
    user = _make_user()
    req = TriageRequest(title="service update", description="scheduled maintenance")

    result = await analyze_text(data=req, current_user=user)

    assert result.priority == "Medium"
    assert result.provider == "keyword"


async def test_analyze_text_with_security_category():
    """手動トリアージ: セキュリティカテゴリ判定"""
    user = _make_user()
    req = TriageRequest(title="unauthorized access detected", description="security breach")

    result = await analyze_text(data=req, current_user=user)

    assert result.category == "Security"


async def test_analyze_text_network_category():
    """手動トリアージ: ネットワークカテゴリ判定"""
    user = _make_user()
    req = TriageRequest(title="DNS resolution failure", description="network connectivity issue")

    result = await analyze_text(data=req, current_user=user)

    assert result.category == "Network"


async def test_analyze_text_infrastructure_category():
    """手動トリアージ: インフラカテゴリ判定"""
    user = _make_user()
    req = TriageRequest(title="Server CPU at 100%", description="disk space running low")

    result = await analyze_text(data=req, current_user=user)

    assert result.category == "Infrastructure"


# ─── POST /ai-triage/incident テスト ───────────────────────────────────────────


async def test_triage_incident_success():
    """インシデントトリアージ: 正常ケース"""
    user = _make_user()
    incident_id = uuid.uuid4()
    req = IncidentTriageRequest(incident_id=incident_id)

    mock_result = AITriageResult(
        priority="High",
        category="Network",
        confidence=0.85,
        reasoning="keyword match",
        provider="keyword",
    )

    db = AsyncMock()
    with patch.object(AITriageService, "apply_triage_to_incident", return_value=mock_result):
        result = await triage_incident(data=req, db=db, current_user=user)

    assert result.priority == "High"
    assert result.category == "Network"
    assert result.provider == "keyword"


async def test_triage_incident_not_found():
    """インシデントトリアージ: インシデント未発見で404"""
    user = _make_user()
    incident_id = uuid.uuid4()
    req = IncidentTriageRequest(incident_id=incident_id)

    mock_result = AITriageResult(
        priority="Unknown",
        category="Unknown",
        confidence=0.0,
        reasoning="Incident not found",
        provider="keyword",
    )

    db = AsyncMock()
    with patch.object(AITriageService, "apply_triage_to_incident", return_value=mock_result):
        with pytest.raises(Exception) as exc_info:
            await triage_incident(data=req, db=db, current_user=user)
        assert exc_info.value.status_code == 404


# ─── POST /ai-triage/batch テスト ─────────────────────────────────────────────


async def test_batch_triage_all_success():
    """バッチトリアージ: 全件成功"""
    user = _make_user()
    ids = [uuid.uuid4(), uuid.uuid4()]
    req = BatchTriageRequest(incident_ids=ids)

    mock_results = [
        {
            "incident_id": str(ids[0]),
            "priority": "Critical",
            "category": "Security",
            "confidence": 0.9,
            "reasoning": "keyword match",
            "success": True,
            "error": None,
        },
        {
            "incident_id": str(ids[1]),
            "priority": "Low",
            "category": "Application",
            "confidence": 0.7,
            "reasoning": "keyword match",
            "success": True,
            "error": None,
        },
    ]

    db = AsyncMock()
    with patch.object(AITriageService, "batch_triage", return_value=mock_results):
        result = await batch_triage(data=req, db=db, current_user=user)

    assert result.total == 2
    assert result.success_count == 2
    assert result.failure_count == 0
    assert result.items[0].priority == "Critical"
    assert result.items[1].priority == "Low"


async def test_batch_triage_partial_failure():
    """バッチトリアージ: 一部失敗"""
    user = _make_user()
    ids = [uuid.uuid4(), uuid.uuid4()]
    req = BatchTriageRequest(incident_ids=ids)

    mock_results = [
        {
            "incident_id": str(ids[0]),
            "priority": "High",
            "category": "Network",
            "confidence": 0.8,
            "reasoning": "keyword match",
            "success": True,
            "error": None,
        },
        {
            "incident_id": str(ids[1]),
            "priority": "Unknown",
            "category": "Unknown",
            "confidence": 0.0,
            "reasoning": "",
            "success": False,
            "error": "DB connection error",
        },
    ]

    db = AsyncMock()
    with patch.object(AITriageService, "batch_triage", return_value=mock_results):
        result = await batch_triage(data=req, db=db, current_user=user)

    assert result.total == 2
    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.items[1].success is False
    assert result.items[1].error == "DB connection error"


# ─── GET /ai-triage/provider テスト ────────────────────────────────────────────


async def test_get_provider_info_keyword():
    """プロバイダー情報: keywordプロバイダー"""
    user = _make_user()

    with patch(
        "src.services.ai_triage_service.get_triage_provider",
        return_value=KeywordTriageProvider(),
    ):
        result = await get_provider_info(current_user=user)

    assert result.provider == "keyword"
    assert result.model is None


async def test_get_provider_info_openai():
    """プロバイダー情報: OpenAIプロバイダー"""
    user = _make_user()

    with patch(
        "src.services.ai_triage_service.get_triage_provider",
        return_value=OpenAITriageProvider("sk-test", "gpt-4o-mini"),
    ):
        result = await get_provider_info(current_user=user)

    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"


async def test_get_provider_info_claude():
    """プロバイダー情報: Claudeプロバイダー"""
    user = _make_user()

    with patch(
        "src.services.ai_triage_service.get_triage_provider",
        return_value=ClaudeTriageProvider("sk-ant-test", "claude-sonnet-4-20250514"),
    ):
        result = await get_provider_info(current_user=user)

    assert result.provider == "claude"
    assert result.model == "claude-sonnet-4-20250514"


# ─── ClaudeTriageProvider テスト ───────────────────────────────────────────────


async def test_claude_provider_fallback_without_package():
    """anthropicパッケージ未インストール時 → KeywordProviderにフォールバック"""
    provider = ClaudeTriageProvider(api_key="sk-ant-test", model="claude-sonnet-4-20250514")

    with patch.dict(sys.modules, {"anthropic": None}):
        result = await provider.analyze("production down", "critical outage")

    assert isinstance(result, AITriageResult)
    assert result.priority == "Critical"
    assert result.provider == "keyword"


async def test_claude_provider_success():
    """Claude APIプロバイダー: 正常レスポンス"""
    provider = ClaudeTriageProvider(api_key="sk-ant-test", model="claude-sonnet-4-20250514")

    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = (
        '{"priority": "High", "category": "Network",'
        ' "confidence": 0.85, "reasoning": "Network issue detected"}'
    )
    mock_response.content = [mock_content]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("src.services.ai_triage_service.anthropic", create=True) as mock_anthropic_mod:
        mock_anthropic_mod.AsyncAnthropic.return_value = mock_client
        # anthropicモジュールのインポートをモック
        with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
            result = await provider.analyze("network outage", "DNS not resolving")

    assert result.priority == "High"
    assert result.category == "Network"
    assert result.confidence == 0.85
    assert result.provider == "claude"


async def test_claude_provider_invalid_priority_fallback():
    """Claude APIプロバイダー: 無効な優先度値のバリデーション"""
    provider = ClaudeTriageProvider(api_key="sk-ant-test", model="claude-sonnet-4-20250514")

    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = (
        '{"priority": "InvalidValue", "category": "InvalidCat",'
        ' "confidence": 0.7, "reasoning": "test"}'
    )
    mock_response.content = [mock_content]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("src.services.ai_triage_service.anthropic", create=True) as mock_anthropic_mod:
        mock_anthropic_mod.AsyncAnthropic.return_value = mock_client
        with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
            result = await provider.analyze("test incident", None)

    assert result.priority == "Medium"
    assert result.category == "Unknown"


# ─── get_triage_provider ファクトリテスト ──────────────────────────────────────


async def test_get_triage_provider_claude_with_key():
    """claude + api_key設定 → ClaudeTriageProvider を返す"""
    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "claude"
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.llm_model = "claude-sonnet-4-20250514"
        mock_settings.openai_api_key = ""
        mock_settings.openai_api_base = ""
        provider = get_triage_provider()
    assert isinstance(provider, ClaudeTriageProvider)
    assert provider.api_key == "sk-ant-test-key"


async def test_get_triage_provider_claude_without_key_falls_back():
    """claude設定だがapi_keyなし → KeywordProvider"""
    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "claude"
        mock_settings.anthropic_api_key = ""
        mock_settings.openai_api_key = ""
        mock_settings.openai_api_base = ""
        mock_settings.llm_model = "claude-sonnet-4-20250514"
        provider = get_triage_provider()
    assert isinstance(provider, KeywordTriageProvider)


# ─── AITriageService バッチトリアージテスト ────────────────────────────────────


async def test_batch_triage_service_success():
    """AITriageService.batch_triage: 正常ケース"""
    svc = AITriageService()
    incident_id = str(uuid.uuid4())

    mock_result = AITriageResult(
        priority="High",
        category="Application",
        confidence=0.8,
        reasoning="test",
        provider="keyword",
    )

    db = AsyncMock()
    with patch.object(svc, "apply_triage_to_incident", return_value=mock_result):
        results = await svc.batch_triage(db, [incident_id])

    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["priority"] == "High"


async def test_batch_triage_service_handles_error():
    """AITriageService.batch_triage: エラーハンドリング"""
    svc = AITriageService()
    incident_id = str(uuid.uuid4())

    db = AsyncMock()
    with patch.object(
        svc,
        "apply_triage_to_incident",
        side_effect=Exception("DB connection failed"),
    ):
        results = await svc.batch_triage(db, [incident_id])

    assert len(results) == 1
    assert results[0]["success"] is False
    assert "DB connection failed" in results[0]["error"]


# ─── provider フィールドテスト ─────────────────────────────────────────────────


async def test_openai_provider_includes_provider_field():
    """OpenAITriageProvider: フォールバック時でもproviderフィールドが設定される"""
    provider = OpenAITriageProvider(api_key="sk-test", model="gpt-4o-mini")

    with patch.dict(sys.modules, {"openai": None}):
        result = await provider.analyze("production down", "critical outage")

    assert result.provider == "keyword"


async def test_keyword_provider_includes_provider_field():
    """KeywordTriageProvider: providerフィールドが'keyword'"""
    provider = KeywordTriageProvider()
    result = await provider.analyze("test title", None)
    assert result.provider == "keyword"


async def test_get_provider_info_method():
    """AITriageService.get_provider_info: 各プロバイダーの情報を正しく返す"""
    svc = AITriageService()

    with patch(
        "src.services.ai_triage_service.get_triage_provider",
        return_value=KeywordTriageProvider(),
    ):
        info = svc.get_provider_info()
    assert info["provider"] == "keyword"
    assert info["model"] is None

    with patch(
        "src.services.ai_triage_service.get_triage_provider",
        return_value=OpenAITriageProvider("key", "gpt-4o"),
    ):
        info = svc.get_provider_info()
    assert info["provider"] == "openai"
    assert info["model"] == "gpt-4o"

    with patch(
        "src.services.ai_triage_service.get_triage_provider",
        return_value=ClaudeTriageProvider("key", "claude-sonnet-4-20250514"),
    ):
        info = svc.get_provider_info()
    assert info["provider"] == "claude"
    assert info["model"] == "claude-sonnet-4-20250514"
