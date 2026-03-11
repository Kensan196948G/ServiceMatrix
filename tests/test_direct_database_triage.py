"""database.py / ai_triage_service.py 追加カバレッジテスト

対象:
  src/core/database.py (47%) - get_db 成功・例外ロールバックパス
  src/services/ai_triage_service.py (88%) - find_similar_incidents 各分岐
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── database.py: get_db ─────────────────────────────────────────────────────


async def test_get_db_success_commits_and_closes():
    """get_db: 正常終了 → session.commit() が呼ばれる（lines 36-44）"""
    from src.core.database import get_db

    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("src.core.database.AsyncSessionLocal", return_value=mock_cm):
        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session
        # ジェネレータを正常終了させる
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    mock_session.commit.assert_called_once()


async def test_get_db_exception_rollbacks():
    """get_db: 例外発生 → session.rollback() が呼ばれ例外が再送出される（lines 40-42）"""
    from src.core.database import get_db

    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("src.core.database.AsyncSessionLocal", return_value=mock_cm):
        gen = get_db()
        await gen.__anext__()  # yield まで進む
        with pytest.raises(ValueError, match="テストエラー"):
            await gen.athrow(ValueError("テストエラー"))

    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()


async def test_get_db_yields_session_object():
    """get_db: yield するセッションオブジェクトが async with の戻り値と一致する"""
    from src.core.database import get_db

    mock_session = AsyncMock()
    mock_session.session_id = "test-session-123"
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("src.core.database.AsyncSessionLocal", return_value=mock_cm):
        sessions_yielded = []
        async for session in get_db():
            sessions_yielded.append(session)

    assert len(sessions_yielded) == 1
    assert sessions_yielded[0] is mock_session


# ─── ai_triage_service.py: find_similar_incidents ──────────────────────────


async def test_find_similar_incidents_empty_query_words_returns_empty():
    """find_similar_incidents: 空タイトル/説明 → 空リスト（line 193-194）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    # 空文字列→query_words=[]→早期リターン
    result = await svc.find_similar_incidents(db, "", None, limit=5)

    assert result == []
    db.execute.assert_not_called()


async def test_find_similar_incidents_with_matching_incidents():
    """find_similar_incidents: 類似インシデントあり → スコア降順リスト返却（lines 200-229）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    # 類似インシデントモック作成
    inc1 = MagicMock()
    inc1.incident_id = uuid.uuid4()
    inc1.incident_number = "INC-2026-000001"
    inc1.title = "データベース接続エラー"
    inc1.description = "PostgreSQLへの接続タイムアウト"

    inc2 = MagicMock()
    inc2.incident_id = uuid.uuid4()
    inc2.incident_number = "INC-2026-000002"
    inc2.title = "サーバーCPU高負荷"
    inc2.description = "CPUが90%以上で継続"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc1, inc2]
    db.execute = AsyncMock(return_value=result_mock)

    result = await svc.find_similar_incidents(
        db, "データベース障害", "PostgreSQL接続エラー", limit=5
    )

    # inc1 は "データベース" 関連なのでスコアあり、inc2 は低スコア
    assert isinstance(result, list)
    assert all("incident_id" in r for r in result)
    assert all("similarity" in r for r in result)
    # スコア降順
    if len(result) > 1:
        assert result[0]["similarity"] >= result[1]["similarity"]


async def test_find_similar_incidents_no_matching_words():
    """find_similar_incidents: 類似語なし → 空リスト（similarity=0のため除外）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    # 全く異なるタイトルのインシデント
    inc = MagicMock()
    inc.incident_id = uuid.uuid4()
    inc.incident_number = "INC-2026-000001"
    inc.title = "zzzzzz xxxxx"
    inc.description = "qqqq wwwww"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc]
    db.execute = AsyncMock(return_value=result_mock)

    result = await svc.find_similar_incidents(
        db, "database error timeout", "connection failed", limit=5
    )

    # 共通語なし → similarity=0 → リストに含まれない
    assert result == []


async def test_find_similar_incidents_incident_with_empty_title():
    """find_similar_incidents: doc_words が空のインシデント → skip（line 205-206）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    # タイトルも説明も1文字以下のインシデント（doc_words=[]になる）
    inc_empty = MagicMock()
    inc_empty.incident_id = uuid.uuid4()
    inc_empty.incident_number = "INC-2026-000001"
    inc_empty.title = "a"  # 1文字 → _normalize でフィルタ
    inc_empty.description = None

    # 普通のインシデント
    inc_normal = MagicMock()
    inc_normal.incident_id = uuid.uuid4()
    inc_normal.incident_number = "INC-2026-000002"
    inc_normal.title = "データベースエラー"
    inc_normal.description = "接続タイムアウト"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [inc_empty, inc_normal]
    db.execute = AsyncMock(return_value=result_mock)

    # inc_empty はスキップされ、inc_normal だけが評価される
    result = await svc.find_similar_incidents(db, "データベース障害", "接続エラー", limit=5)

    # inc_empty はスキップ（doc_words=[] → continue）
    incident_ids = [r["incident_id"] for r in result]
    assert str(inc_empty.incident_id) not in incident_ids


async def test_find_similar_incidents_limit_applied():
    """find_similar_incidents: limit パラメータが適用される（line 229）"""
    from src.services.ai_triage_service import AITriageService

    svc = AITriageService()
    db = AsyncMock()

    # 10件の類似インシデントを用意
    incidents = []
    for i in range(10):
        inc = MagicMock()
        inc.incident_id = uuid.uuid4()
        inc.incident_number = f"INC-2026-{i:06d}"
        inc.title = f"データベース障害テスト{i}"
        inc.description = "DB接続タイムアウト"
        incidents.append(inc)

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = incidents
    db.execute = AsyncMock(return_value=result_mock)

    result = await svc.find_similar_incidents(db, "データベース障害", "DB接続", limit=3)

    assert len(result) <= 3


async def test_find_similar_incidents_openai_api_base_branch():
    """get_triage_provider: ollama + openai_api_base → OllamaTriageProvider（設計改善: Ollama専用クラス分離）"""
    from src.services.ai_triage_service import OllamaTriageProvider, get_triage_provider

    with patch("src.services.ai_triage_service.settings") as mock_settings:
        mock_settings.llm_provider = "ollama"
        mock_settings.openai_api_key = ""
        mock_settings.llm_model = "llama3"
        mock_settings.openai_api_base = "http://localhost:11434/v1"

        provider = get_triage_provider()

    assert isinstance(provider, OllamaTriageProvider)
    assert provider.base_url == "http://localhost:11434/v1"
