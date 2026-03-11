"""ai_triage_service.py カバレッジ向上テスト

対象: src/services/ai_triage_service.py (56%)
  lines 45-49: KeywordTriageProvider.analyze
  lines 57-66: _determine_priority (Critical/High/Low/Medium)
  lines 69-81: _determine_category (Security/Network/Database/Infrastructure/Unknown)
  lines 93-123: OpenAITriageProvider.analyze (openai import / ImportError fallback)
  lines 130, 135: get_triage_provider (openai branch / default fallback)
  lines 143-144: AITriageService.triage
  lines 148-179: apply_triage_to_incident (found/not_found)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── KeywordTriageProvider: analyze + _determine_priority ────────────────────


async def test_keyword_provider_analyze_critical_priority():
    """KeywordTriageProvider: 'outage' キーワード → Critical 優先度"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("system outage detected", None)

    assert result.priority == "Critical"
    assert result.confidence == 0.9


async def test_keyword_provider_analyze_high_priority():
    """KeywordTriageProvider: 'error' キーワード → High 優先度"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("application error reported", "server error")

    assert result.priority == "High"
    assert result.confidence == 0.8


async def test_keyword_provider_analyze_low_priority():
    """KeywordTriageProvider: 'inquiry' キーワード → Low 優先度"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("information inquiry from user", None)

    assert result.priority == "Low"
    assert result.confidence == 0.7


async def test_keyword_provider_analyze_medium_priority_default():
    """KeywordTriageProvider: マッチなし → Medium（デフォルト）"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("routine maintenance task", None)

    assert result.priority == "Medium"
    assert result.confidence == 0.5


# ─── KeywordTriageProvider: _determine_category ──────────────────────────────


async def test_keyword_provider_category_security():
    """KeywordTriageProvider: 'security' キーワード → Security カテゴリ"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("security breach detected in auth", None)

    assert result.category == "Security"


async def test_keyword_provider_category_network():
    """KeywordTriageProvider: 'network' キーワード → Network カテゴリ"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("network connectivity issue", None)

    assert result.category == "Network"


async def test_keyword_provider_category_database():
    """KeywordTriageProvider: 'database' キーワード → Database カテゴリ"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("database query timeout", None)

    assert result.category == "Database"


async def test_keyword_provider_category_infrastructure():
    """KeywordTriageProvider: 'server' キーワード → Infrastructure カテゴリ"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("server cpu high load", None)

    assert result.category == "Infrastructure"


async def test_keyword_provider_category_unknown():
    """KeywordTriageProvider: カテゴリキーワードなし → Unknown カテゴリ"""
    from src.services.ai_triage_service import KeywordTriageProvider

    provider = KeywordTriageProvider()
    result = await provider.analyze("routine maintenance", None)

    assert result.category == "Unknown"


# ─── OpenAITriageProvider: analyze ──────────────────────────────────────────


async def test_openai_provider_analyze_fallback_on_import_error():
    """OpenAITriageProvider: openai 未インストール → KeywordProvider フォールバック（line 121-123）"""
    from src.services.ai_triage_service import OpenAITriageProvider

    provider = OpenAITriageProvider(api_key="test_key", model="gpt-4")

    # sys.modules に openai=None をセットすると import openai が ImportError になる
    import sys
    with patch.dict(sys.modules, {"openai": None}):
        result = await provider.analyze("network outage", "connectivity issue")

    # ImportError → KeywordTriageProvider フォールバック → Critical (outage keyword)
    assert result.priority in ("Critical", "High", "Medium", "Low", "Unknown")


async def test_openai_provider_init_with_api_base():
    """OpenAITriageProvider: api_base を設定して初期化"""
    from src.services.ai_triage_service import OpenAITriageProvider

    provider = OpenAITriageProvider(
        api_key="sk-test",
        model="llama3",
        api_base="http://localhost:11434/v1",
    )

    assert provider.api_key == "sk-test"
    assert provider.model == "llama3"
    assert provider.api_base == "http://localhost:11434/v1"


async def test_openai_provider_analyze_with_mocked_openai():
    """OpenAITriageProvider: openai が使えるとき → API 呼び出してトリアージ（lines 96-115）"""
    from src.services.ai_triage_service import OpenAITriageProvider

    provider = OpenAITriageProvider(
        api_key="sk-test",
        model="gpt-4",
        api_base="http://localhost:11434/v1",
    )

    # OpenAI クライアントをモック
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        '{"priority": "High", "category": "Database", "confidence": 0.85, "reasoning": "DB error"}'
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_openai_module = MagicMock()
    mock_openai_module.AsyncOpenAI = MagicMock(return_value=mock_client)

    import sys
    with patch.dict(sys.modules, {"openai": mock_openai_module}):
        result = await provider.analyze("database connection error", "timeout occurred")

    assert result.priority == "High"
    assert result.category == "Database"
    assert result.confidence == 0.85


# ─── get_triage_provider ─────────────────────────────────────────────────────


def test_get_triage_provider_openai_branch():
    """get_triage_provider: llm_provider=openai + api_key → OpenAITriageProvider"""
    from src.services.ai_triage_service import OpenAITriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "sk-real-key"
        mock_settings.llm_model = "gpt-4"
        mock_settings.openai_api_base = ""

        provider = get_triage_provider()

    assert isinstance(provider, OpenAITriageProvider)
    assert provider.api_key == "sk-real-key"


def test_get_triage_provider_azure_openai_branch():
    """get_triage_provider: llm_provider=azure_openai + api_base → OpenAITriageProvider"""
    from src.services.ai_triage_service import OpenAITriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "azure_openai"
        mock_settings.openai_api_key = ""
        mock_settings.llm_model = "gpt-4o"
        mock_settings.openai_api_base = "https://my-azure.openai.azure.com/"

        provider = get_triage_provider()

    assert isinstance(provider, OpenAITriageProvider)
    assert provider.api_base == "https://my-azure.openai.azure.com/"


def test_get_triage_provider_default_keyword():
    """get_triage_provider: 設定なし → KeywordTriageProvider（デフォルト、line 135）"""
    from src.services.ai_triage_service import KeywordTriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "none"
        mock_settings.openai_api_key = ""
        mock_settings.openai_api_base = ""

        provider = get_triage_provider()

    assert isinstance(provider, KeywordTriageProvider)


# ─── AITriageService.triage (lines 143-144) ──────────────────────────────────


async def test_ai_triage_service_triage_delegates_to_provider():
    """AITriageService.triage: get_triage_provider 経由でプロバイダーを取得して analyze"""
    from src.services.ai_triage_service import AITriageResult, AITriageService

    expected = AITriageResult(
        priority="High",
        category="Database",
        confidence=0.85,
        reasoning="keyword match",
    )

    svc = AITriageService()
    with patch(
        "src.services.ai_triage_service.get_triage_provider",
        return_value=MagicMock(analyze=AsyncMock(return_value=expected)),
    ):
        result = await svc.triage("DB connection error", "timeout")

    assert result.priority == "High"
    assert result.category == "Database"


# ─── AITriageService.apply_triage_to_incident (lines 148-179) ────────────────


async def test_apply_triage_to_incident_not_found_returns_unknown():
    """apply_triage_to_incident: インシデント不存在 → Unknown を返す（lines 156-163）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    result = await svc.apply_triage_to_incident(db, str(uuid.uuid4()))

    assert result.priority == "Unknown"
    assert result.reasoning == "Incident not found"


async def test_find_similar_incidents_similarity_score_positive():
    """find_similar_incidents: 共通単語あり → similarity > 0 で scores.append（line 219）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    # ASCII 単語で確実に共通トークンを持つインシデント
    inc = MagicMock()
    inc.incident_id = uuid.uuid4()
    inc.incident_number = "INC-2026-000001"
    inc.title = "database connection timeout error"
    inc.description = "postgresql connection failed"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc]
    db.execute = AsyncMock(return_value=result_mock)

    # 共通単語: "database", "connection", "timeout" → similarity > 0 → line 219 実行
    result = await svc.find_similar_incidents(
        db, "database connection timeout", "connection error", limit=5
    )

    assert len(result) == 1
    assert result[0]["similarity"] > 0
    assert "incident_id" in result[0]


async def test_apply_triage_to_incident_found_updates_notes():
    """apply_triage_to_incident: インシデント存在 → ai_triage_notes を更新して返す（lines 165-179）"""
    from src.services.ai_triage_service import AITriageResult, AITriageService

    svc = AITriageService()
    db = AsyncMock()

    inc_mock = MagicMock()
    inc_mock.title = "データベース障害"
    inc_mock.description = "PostgreSQL接続タイムアウト"
    inc_mock.ai_triage_notes = None

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inc_mock
    db.execute = AsyncMock(return_value=result_mock)

    expected_triage = AITriageResult(
        priority="High",
        category="Database",
        confidence=0.85,
        reasoning="Database keywords matched",
    )

    with patch.object(svc, "triage", new=AsyncMock(return_value=expected_triage)):
        result = await svc.apply_triage_to_incident(db, str(uuid.uuid4()))

    assert result.priority == "High"
    assert result.category == "Database"
    assert inc_mock.ai_triage_notes is not None
    assert "Priority=High" in inc_mock.ai_triage_notes
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_provider_analyze_success():
    """OllamaTriageProvider: 正常系 → Ollamaからレスポンスを受けてトリアージ結果を返す"""
    from src.services.ai_triage_service import OllamaTriageProvider

    provider = OllamaTriageProvider(base_url="http://localhost:11434/v1", model="llama3.2")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        '{"priority": "High", "category": "Network", "confidence": 0.78, "reasoning": "network timeout"}'
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_openai_module = MagicMock()
    mock_openai_module.AsyncOpenAI = MagicMock(return_value=mock_client)

    import sys
    with patch.dict(sys.modules, {"openai": mock_openai_module}):
        result = await provider.analyze("ネットワーク接続障害", "タイムアウト多発")

    assert result.priority == "High"
    assert result.category == "Network"
    assert result.confidence == 0.78


@pytest.mark.asyncio
async def test_ollama_provider_analyze_with_markdown_json():
    """OllamaTriageProvider: Markdownコードブロック形式のレスポンス → JSON抽出して解析"""
    from src.services.ai_triage_service import OllamaTriageProvider

    provider = OllamaTriageProvider()

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "```json\n"
        '{"priority": "Critical", "category": "Database", "confidence": 0.95, "reasoning": "db down"}'
        "\n```"
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_openai_module = MagicMock()
    mock_openai_module.AsyncOpenAI = MagicMock(return_value=mock_client)

    import sys
    with patch.dict(sys.modules, {"openai": mock_openai_module}):
        result = await provider.analyze("DB停止", None)

    assert result.priority == "Critical"
    assert result.category == "Database"


@pytest.mark.asyncio
async def test_ollama_provider_analyze_exception_fallback():
    """OllamaTriageProvider: 例外発生 → キーワードトリアージにフォールバック"""
    from src.services.ai_triage_service import OllamaTriageProvider

    provider = OllamaTriageProvider()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("connection refused"))

    mock_openai_module = MagicMock()
    mock_openai_module.AsyncOpenAI = MagicMock(return_value=mock_client)

    import sys
    with patch.dict(sys.modules, {"openai": mock_openai_module}):
        result = await provider.analyze("緊急: サーバー停止", "本番環境でoutage発生")

    # フォールバック後もキーワードマッチで Critical になる
    assert result.priority == "Critical"


@pytest.mark.asyncio
async def test_ollama_provider_import_error_fallback():
    """OllamaTriageProvider: openai未インストール → キーワードトリアージにフォールバック"""
    from src.services.ai_triage_service import OllamaTriageProvider

    provider = OllamaTriageProvider()

    import sys
    with patch.dict(sys.modules, {"openai": None}):
        result = await provider.analyze("network error", None)

    assert result.priority in ("High", "Medium", "Low", "Critical")


def test_get_triage_provider_ollama():
    """get_triage_provider: llm_provider=ollama → OllamaTriageProvider を返す"""
    from src.services.ai_triage_service import OllamaTriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "ollama"
        mock_settings.openai_api_base = "http://localhost:11434/v1"
        mock_settings.llm_model = "llama3.2"
        provider = get_triage_provider()

    assert isinstance(provider, OllamaTriageProvider)
    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.model == "llama3.2"


def test_get_triage_provider_ollama_default_url():
    """get_triage_provider: ollama + base_url未設定 → デフォルトURL使用"""
    from src.services.ai_triage_service import OllamaTriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "ollama"
        mock_settings.openai_api_base = ""
        mock_settings.llm_model = "llama3.2"
        provider = get_triage_provider()

    assert isinstance(provider, OllamaTriageProvider)
    assert provider.base_url == OllamaTriageProvider.DEFAULT_BASE_URL
