"""セマンティック検索サービス・APIエンドポイントのテスト

対象:
  - src/services/semantic_search_service.py
  - src/api/v1/search.py (POST /semantic, GET /suggest)

テスト戦略:
  - sentence_transformers 未インストール環境（CI）でも全テスト通過
  - キーワードフォールバックモードを前提とする
  - エンドポイントは直接呼び出しパターンで非同期カバレッジを確保
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 非同期テスト関数のみに asyncio マークを適用する（クラス内同期テストを除く）


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


def _make_incident_row(title: str = "テストインシデント", description: str = "説明文"):
    row = MagicMock()
    row.incident_id = uuid.uuid4()
    row.incident_number = "INC-2026-000001"
    row.title = title
    row.description = description
    row.status = "New"
    row.priority = "P3"
    return row


def _make_execute_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _make_execute_result_rows(rows):
    """scalars() を使わずに all() を返す（suggest用）"""
    result = MagicMock()
    result.all.return_value = rows
    return result


def _make_db_semantic(incidents):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result(incidents))
    return db


def _make_db_suggest(rows):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_execute_result_rows(rows))
    return db


# ─── SemanticSearchService ユニットテスト ────────────────────────────────────


class TestKeywordSearchScore:
    """keyword_search_score メソッドのテスト"""

    def test_keyword_search_score_match(self):
        """クエリとテキストが一致する場合スコアが 1.0 になる"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        score = svc.keyword_search_score("network failure", "network failure")
        assert score == 1.0

    def test_keyword_search_score_partial_match(self):
        """部分一致の場合スコアが 0 < score < 1.0 になる"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        score = svc.keyword_search_score("network failure", "network issue")
        assert 0.0 < score < 1.0

    def test_keyword_search_score_no_match(self):
        """クエリとテキストが一致しない場合スコアが 0.0 になる"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        score = svc.keyword_search_score("database", "network failure")
        assert score == 0.0

    def test_keyword_search_score_empty_query(self):
        """空クエリの場合スコアが 0.0 になる"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        score = svc.keyword_search_score("", "network failure")
        assert score == 0.0


class TestSearchIncidentsByKeywords:
    """search_incidents_by_keywords メソッドのテスト"""

    def test_search_incidents_by_keywords(self):
        """クエリに一致するインシデントが返される"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        incidents = [
            {"title": "network failure", "description": "network is down"},
            {"title": "disk full", "description": "storage issue"},
            {"title": "login error", "description": "auth failure"},
        ]
        results = svc.search_incidents_by_keywords("network", incidents)
        assert len(results) > 0
        assert all("similarity_score" in r for r in results)
        # network を含むインシデントが上位に来る
        assert results[0]["title"] == "network failure"

    def test_search_incidents_by_keywords_no_match(self):
        """一致するインシデントがない場合は空リストを返す"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        incidents = [
            {"title": "disk full", "description": "storage"},
        ]
        results = svc.search_incidents_by_keywords("network", incidents)
        assert results == []

    def test_search_incidents_by_keywords_limit(self):
        """結果が最大10件に制限される"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        # 15件の一致するインシデントを作成
        incidents = [
            {"title": f"network issue {i}", "description": "network problem"}
            for i in range(15)
        ]
        results = svc.search_incidents_by_keywords("network", incidents)
        assert len(results) <= 10

    def test_search_incidents_sorted_by_score(self):
        """結果がスコアの高い順に並ぶ"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        incidents = [
            {"title": "network failure", "description": "network is down"},
            {"title": "network issue database failure", "description": "network database"},
        ]
        results = svc.search_incidents_by_keywords("network failure", incidents)
        if len(results) >= 2:
            assert results[0]["similarity_score"] >= results[1]["similarity_score"]


class TestSemanticServiceEncoding:
    """encode メソッドのテスト"""

    def test_semantic_service_encode_fallback(self):
        """sentence_transformers 未インストール時に encode が None を返す"""
        from src.services.semantic_search_service import SemanticSearchService

        svc = SemanticSearchService()
        # CIではフォールバックモードのはず
        if not svc._use_vector_search:
            result = svc.encode("テストテキスト")
            assert result is None

    def test_semantic_service_no_vector_search_flag(self):
        """sentence_transformers 未インストール時に _use_vector_search が False"""
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            from src.services.semantic_search_service import SemanticSearchService

            svc = SemanticSearchService.__new__(SemanticSearchService)
            svc._encoder = None
            svc._use_vector_search = False
            svc._try_load_encoder()
            assert svc._use_vector_search is False


# ─── APIエンドポイント直接呼び出しテスト ─────────────────────────────────────


@pytest.mark.asyncio
async def test_semantic_search_endpoint():
    """POST /api/v1/search/semantic エンドポイントが動作する"""
    from src.api.v1.search import semantic_search

    mock_user = MagicMock()
    inc1 = _make_incident_row("ネットワーク障害", "ネットワークが停止")
    inc2 = _make_incident_row("ディスク満杯", "ストレージ不足")
    db = _make_db_semantic([inc1, inc2])

    result = await semantic_search(
        db=db,
        current_user=mock_user,
        query="ネットワーク",
        limit=10,
    )

    assert "query" in result
    assert result["query"] == "ネットワーク"
    assert "mode" in result
    assert result["mode"] in ("vector", "keyword")
    assert "count" in result
    assert "results" in result
    assert isinstance(result["results"], list)


@pytest.mark.asyncio
async def test_semantic_search_endpoint_empty_db():
    """DBにインシデントがない場合は空の結果を返す"""
    from src.api.v1.search import semantic_search

    mock_user = MagicMock()
    db = _make_db_semantic([])

    result = await semantic_search(
        db=db,
        current_user=mock_user,
        query="ネットワーク障害",
        limit=10,
    )

    assert result["count"] == 0
    assert result["results"] == []


@pytest.mark.asyncio
async def test_semantic_search_endpoint_with_limit():
    """limit パラメータで結果件数を制限できる"""
    from src.api.v1.search import semantic_search

    mock_user = MagicMock()
    # 5件のインシデントを作成（全てネットワーク関連）
    incidents = [_make_incident_row(f"network issue {i}", "network") for i in range(5)]
    db = _make_db_semantic(incidents)

    result = await semantic_search(
        db=db,
        current_user=mock_user,
        query="network",
        limit=3,
    )

    assert result["count"] <= 3
    assert len(result["results"]) <= 3


@pytest.mark.asyncio
async def test_search_suggest_endpoint():
    """GET /api/v1/search/suggest エンドポイントが動作する"""
    from src.api.v1.search import search_suggest

    mock_user = MagicMock()

    # suggest 用の行モック
    row1 = MagicMock()
    row1.title = "ネットワーク障害"
    row1.incident_number = "INC-2026-000001"
    row2 = MagicMock()
    row2.title = "ネットワーク遅延"
    row2.incident_number = "INC-2026-000002"

    db = _make_db_suggest([row1, row2])

    result = await search_suggest(
        db=db,
        current_user=mock_user,
        q="ネットワーク",
        limit=5,
    )

    assert "query" in result
    assert result["query"] == "ネットワーク"
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)
    assert len(result["suggestions"]) == 2
    assert result["suggestions"][0]["title"] == "ネットワーク障害"
    assert result["suggestions"][0]["incident_number"] == "INC-2026-000001"


@pytest.mark.asyncio
async def test_search_suggest_endpoint_empty():
    """サジェスト結果なしの場合は空リストを返す"""
    from src.api.v1.search import search_suggest

    mock_user = MagicMock()
    db = _make_db_suggest([])

    result = await search_suggest(
        db=db,
        current_user=mock_user,
        q="存在しないキーワード",
        limit=5,
    )

    assert result["suggestions"] == []
