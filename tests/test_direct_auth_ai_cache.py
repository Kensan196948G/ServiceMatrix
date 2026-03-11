"""auth.py / ai_service.py / ai_triage_service.py / cache.py 直接呼び出しテスト

対象:
  src/api/v1/auth.py (82.5%) - create_user重複/無効ロール/成功
  src/services/ai_service.py (81%) - ライブAPI分岐・例外フォールバック
  src/services/ai_triage_service.py (79.8%) - OpenAI/ファクトリ/apply_triage
  src/core/cache.py (80.4%) - 全関数の成功・例外パス
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── auth.py: create_user ──────────────────────────────────────────────────────


async def test_create_user_duplicate_raises_400():
    """create_user: 重複ユーザー → 400（lines 129-130）"""
    from fastapi import HTTPException

    from src.api.v1.auth import create_user
    from src.schemas.auth import UserCreateRequest

    # db.execute が重複ユーザーを返す
    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = MagicMock()  # 既存ユーザー
    db = AsyncMock()
    db.execute = AsyncMock(return_value=dup_result)

    body = UserCreateRequest(
        username="existing_user",
        email="existing@example.com",
        password="password123",
        role="Operator",
    )
    current_user = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await create_user(body=body, current_user=current_user, db=db)

    assert exc_info.value.status_code == 400
    assert "すでに使用されています" in exc_info.value.detail


async def test_create_user_invalid_role_raises_400():
    """create_user: 無効なロール → 400（lines 134-137）"""
    from fastapi import HTTPException

    from src.api.v1.auth import create_user
    from src.schemas.auth import UserCreateRequest

    # db.execute が重複なしを返す（None）
    no_dup_result = MagicMock()
    no_dup_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=no_dup_result)

    body = UserCreateRequest(
        username="newuser",
        email="new@example.com",
        password="password123",
        role="INVALID_ROLE_XYZ",  # UserRole に存在しない
    )
    current_user = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await create_user(body=body, current_user=current_user, db=db)

    assert exc_info.value.status_code == 400
    assert "無効なロール" in exc_info.value.detail


async def test_create_user_success():
    """create_user: 正常作成 → User オブジェクト返却（lines 139-150）

    Note: select(User) に MagicMock を渡すと SQLAlchemy がエラーになるため
    User クラスはそのまま使い、db.add/flush をモックする。
    """
    from src.api.v1.auth import create_user
    from src.schemas.auth import UserCreateRequest

    # db.execute が重複なしを返す
    no_dup_result = MagicMock()
    no_dup_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=no_dup_result)
    db.add = MagicMock()  # db.add は同期呼び出し

    body = UserCreateRequest(
        username="newuser",
        email="new@example.com",
        password="password123",
        role="Operator",  # UserRole.OPERATOR の値は "Operator"
    )
    current_user = MagicMock()

    result = await create_user(body=body, current_user=current_user, db=db)

    db.add.assert_called_once()
    db.flush.assert_called_once()
    # result は User ORM インスタンス
    assert result.username == "newuser"


# ─── ai_service.py: AIService ──────────────────────────────────────────────────


def _make_ai_service(provider="live", api_key="test-key"):
    """ライブAPI呼び出しパスを有効にした AIService インスタンス"""
    from src.services.ai_service import AIService

    svc = AIService()
    svc.provider = provider
    svc.api_key = api_key
    svc.model = "gpt-4o-mini"
    return svc


def _make_httpx_mock(response_json: dict):
    """httpx.AsyncClient の async context manager モック"""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = response_json

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


async def test_ai_service_summarize_incident_live_success():
    """AIService.summarize_incident: ライブAPI成功パス（lines 36-47）"""
    svc = _make_ai_service()
    response_json = {"choices": [{"message": {"content": "AI要約テキスト"}}]}
    mock_client = _make_httpx_mock(response_json)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.summarize_incident(
            incident_title="DB障害",
            description="データベース接続タイムアウト",
            comments=["調査中", "復旧作業開始"],
        )

    assert result == "AI要約テキスト"
    mock_client.post.assert_called_once()


async def test_ai_service_summarize_incident_live_exception_fallback():
    """AIService.summarize_incident: 例外 → フォールバック（lines 48-49）"""
    svc = _make_ai_service()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=Exception("API接続エラー"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.summarize_incident(
            incident_title="DB障害",
            description="詳細説明",
            comments=[],
        )

    # フォールバック: "[AI要約] {title}: {description[:100]}..."
    assert result.startswith("[AI要約]")
    assert "DB障害" in result


async def test_ai_service_generate_rca_report_live_success():
    """AIService.generate_rca_report: ライブAPI成功パス（lines 79-93）"""
    import json

    svc = _make_ai_service()
    rca_data = {
        "root_cause": "DBのディスク容量不足",
        "contributing_factors": ["監視未設定"],
        "recommendations": ["容量拡張"],
        "prevention_measures": ["アラート設定"],
    }
    response_json = {"choices": [{"message": {"content": json.dumps(rca_data)}}]}
    mock_client = _make_httpx_mock(response_json)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.generate_rca_report(
            problem_title="DB障害",
            affected_services=["OrderAPI", "InventoryAPI"],
            timeline=["12:00 障害発生", "12:30 復旧"],
        )

    assert result["root_cause"] == "DBのディスク容量不足"
    assert "recommendations" in result


async def test_ai_service_generate_rca_report_live_exception_fallback():
    """AIService.generate_rca_report: 例外 → フォールバック（lines 94-100）"""
    svc = _make_ai_service()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=ConnectionError("タイムアウト"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.generate_rca_report(
            problem_title="障害",
            affected_services=[],
            timeline=[],
        )

    assert "root_cause" in result
    assert "調査中" in result["root_cause"]


async def test_ai_service_suggest_priority_live_valid_result():
    """AIService.suggest_incident_priority: ライブAPI → 有効優先度返却（lines 126-140）"""
    svc = _make_ai_service()
    response_json = {"choices": [{"message": {"content": "P1"}}]}
    mock_client = _make_httpx_mock(response_json)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.suggest_incident_priority(
            title="本番DB全停止",
            description="全サービス停止",
            affected_service="OrderAPI",
        )

    assert result == "P1"


async def test_ai_service_suggest_priority_live_invalid_result_fallback_p3():
    """AIService.suggest_incident_priority: 無効な優先度 → P3（lines 138-140）"""
    svc = _make_ai_service()
    response_json = {"choices": [{"message": {"content": "INVALID"}}]}
    mock_client = _make_httpx_mock(response_json)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.suggest_incident_priority(
            title="軽微な問題",
            description="説明",
            affected_service=None,
        )

    assert result == "P3"


async def test_ai_service_suggest_priority_live_exception_fallback():
    """AIService.suggest_incident_priority: 例外 → P3（line 141-142）"""
    svc = _make_ai_service()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=Exception("ネットワークエラー"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.suggest_incident_priority(
            title="問題",
            description="説明",
            affected_service=None,
        )

    assert result == "P3"


# ─── ai_triage_service.py: OpenAITriageProvider ────────────────────────────────


async def test_openai_triage_provider_import_error_fallback():
    """OpenAITriageProvider: openaiパッケージ未インストール → KeywordProvider フォールバック（line 121-123）"""
    from src.services.ai_triage_service import OpenAITriageProvider

    provider = OpenAITriageProvider(api_key="test-key", model="gpt-4o-mini")

    with patch.dict("sys.modules", {"openai": None}):
        result = await provider.analyze("サーバー障害", "全サービス停止")

    # KeywordProvider にフォールバック → Critical になるはず
    assert result.priority in ("Critical", "High", "Medium", "Low")
    assert result.category is not None


async def test_openai_triage_provider_analyze_success():
    """OpenAITriageProvider: analyze 正常パス（lines 92-120）"""
    import json

    from src.services.ai_triage_service import OpenAITriageProvider

    provider = OpenAITriageProvider(api_key="test-key", model="gpt-4o-mini")

    response_data = {
        "priority": "High",
        "category": "Network",
        "confidence": 0.85,
        "reasoning": "ネットワーク障害のため",
    }

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(response_data)

    mock_openai_client = AsyncMock()
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_openai_module = MagicMock()
    mock_openai_module.AsyncOpenAI.return_value = mock_openai_client

    with patch.dict("sys.modules", {"openai": mock_openai_module}):
        result = await provider.analyze("ネットワーク障害", "接続タイムアウト")

    assert result.priority == "High"
    assert result.category == "Network"
    assert result.confidence == 0.85


async def test_get_triage_provider_openai_branch():
    """get_triage_provider: openai + openai_api_key → OpenAITriageProvider（lines 129-130）"""
    from src.services.ai_triage_service import OpenAITriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.llm_model = "gpt-4o-mini"
        mock_settings.openai_api_base = ""

        provider = get_triage_provider()

    assert isinstance(provider, OpenAITriageProvider)


async def test_get_triage_provider_azure_branch():
    """get_triage_provider: azure_openai + openai_api_base → OpenAITriageProvider（lines 131-134）"""
    from src.services.ai_triage_service import OpenAITriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "azure_openai"
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.llm_model = "gpt-4o"
        mock_settings.openai_api_base = "https://myinstance.openai.azure.com/"

        provider = get_triage_provider()

    assert isinstance(provider, OpenAITriageProvider)


async def test_apply_triage_to_incident_not_found():
    """apply_triage_to_incident: インシデント不存在 → Unknown を返す（lines 156-163）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    result = await svc.apply_triage_to_incident(db, str(uuid.uuid4()))

    assert result.priority == "Unknown"
    assert result.category == "Unknown"
    assert result.confidence == 0.0


async def test_apply_triage_to_incident_success():
    """apply_triage_to_incident: インシデント存在 → トリアージ実行・flush（lines 165-178）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    incident_mock = MagicMock()
    incident_mock.incident_id = uuid.uuid4()
    incident_mock.title = "本番DB停止"
    incident_mock.description = "クリティカル障害"
    incident_mock.ai_triage_notes = None

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = incident_mock
    db.execute = AsyncMock(return_value=result_mock)

    result = await svc.apply_triage_to_incident(db, str(incident_mock.incident_id))

    assert result.priority in ("Critical", "High", "Medium", "Low")
    assert result.category is not None
    db.flush.assert_called_once()
    assert incident_mock.ai_triage_notes is not None


# ─── cache.py ─────────────────────────────────────────────────────────────────


async def test_cache_get_success():
    """cache_get: Redis成功 → 値を返す（lines 25-32）"""
    from src.core.cache import cache_get

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="cached_value")

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        result = await cache_get("test:key")

    assert result == "cached_value"


async def test_cache_get_exception_returns_none():
    """cache_get: Redis例外 → None（lines 30-32）"""
    from src.core.cache import cache_get

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=Exception("接続エラー"))

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        result = await cache_get("test:key")

    assert result is None


async def test_cache_set_success():
    """cache_set: Redis成功（lines 35-41）"""
    from src.core.cache import cache_set

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await cache_set("test:key", "value", ttl=60)

    mock_redis.set.assert_called_once_with("test:key", "value", ex=60)


async def test_cache_set_exception_no_raise():
    """cache_set: Redis例外 → 例外を飲み込む（lines 40-41）"""
    from src.core.cache import cache_set

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(side_effect=Exception("書き込みエラー"))

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await cache_set("test:key", "value")  # 例外なし


async def test_cache_delete_success():
    """cache_delete: Redis成功（lines 44-50）"""
    from src.core.cache import cache_delete

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=1)

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await cache_delete("test:key")

    mock_redis.delete.assert_called_once_with("test:key")


async def test_cache_delete_exception_no_raise():
    """cache_delete: Redis例外 → 例外を飲み込む（lines 49-50）"""
    from src.core.cache import cache_delete

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(side_effect=Exception("削除エラー"))

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await cache_delete("test:key")  # 例外なし


async def test_cache_delete_pattern_success():
    """cache_delete_pattern: scan_iter でキー削除（lines 53-60）"""
    from src.core.cache import cache_delete_pattern

    mock_redis = AsyncMock()

    async def _async_gen(*args, **kwargs):
        for key in ["incidents:1", "incidents:2"]:
            yield key

    mock_redis.scan_iter = _async_gen
    mock_redis.delete = AsyncMock(return_value=1)

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await cache_delete_pattern("incidents:*")

    assert mock_redis.delete.call_count == 2


async def test_cache_delete_pattern_exception_no_raise():
    """cache_delete_pattern: Redis例外 → 例外を飲み込む（lines 59-60）"""
    from src.core.cache import cache_delete_pattern

    mock_redis = AsyncMock()
    mock_redis.scan_iter = AsyncMock(side_effect=Exception("スキャンエラー"))

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await cache_delete_pattern("incidents:*")  # 例外なし


async def test_add_token_to_blacklist_success():
    """add_token_to_blacklist: Redis成功（lines 63-70）"""
    from src.core.cache import add_token_to_blacklist

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await add_token_to_blacklist("jwt.token.here", expire_seconds=3600)

    mock_redis.set.assert_called_once_with("blacklist:jwt.token.here", "1", ex=3600)


async def test_add_token_to_blacklist_exception_no_raise():
    """add_token_to_blacklist: Redis例外 → 例外を飲み込む（lines 69-70）"""
    from src.core.cache import add_token_to_blacklist

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(side_effect=Exception("Redisエラー"))

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        await add_token_to_blacklist("some.token")  # 例外なし


async def test_is_token_blacklisted_true():
    """is_token_blacklisted: 存在する → True（lines 73-79）"""
    from src.core.cache import is_token_blacklisted

    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=1)

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        result = await is_token_blacklisted("blacklisted.token")

    assert result is True


async def test_is_token_blacklisted_false():
    """is_token_blacklisted: 存在しない → False"""
    from src.core.cache import is_token_blacklisted

    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        result = await is_token_blacklisted("valid.token")

    assert result is False


async def test_is_token_blacklisted_exception_returns_false():
    """is_token_blacklisted: Redis例外 → False（lines 80-82）"""
    from src.core.cache import is_token_blacklisted

    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(side_effect=Exception("Redisダウン"))

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        result = await is_token_blacklisted("some.token")

    assert result is False
