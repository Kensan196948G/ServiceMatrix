"""セマンティック検索サービス - ベクトル類似度検索"""
# sentence-transformers は本番環境でのみ使用
# インストール方法: pip install sentence-transformers
# CIには含めない（重量ライブラリのため）
import structlog

logger = structlog.get_logger(__name__)


class SemanticSearchService:
    """
    テキストのセマンティック検索サービス。
    本番では pgvector + SentenceTransformers を使用。
    テスト/開発環境では キーワードベースのフォールバックを使用。
    """

    def __init__(self):
        self._encoder = None
        self._use_vector_search = False
        self._try_load_encoder()

    def _try_load_encoder(self):
        """SentenceTransformers エンコーダーの読み込みを試みる"""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            self._encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self._use_vector_search = True
            logger.info("semantic_encoder_loaded")
        except ImportError:
            logger.warning("sentence_transformers_not_available_using_keyword_fallback")
            self._use_vector_search = False

    def encode(self, text: str) -> list[float] | None:
        """テキストをベクトルに変換"""
        if not self._use_vector_search or self._encoder is None:
            return None
        try:
            embedding = self._encoder.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error("encode_failed", error=str(e))
            return None

    def keyword_search_score(self, query: str, text: str) -> float:
        """キーワードベースの類似度スコア（フォールバック用）"""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.0
        intersection = query_words & text_words
        return len(intersection) / len(query_words)

    def search_incidents_by_keywords(
        self, query: str, incidents: list[dict]
    ) -> list[dict]:
        """キーワードベースでインシデントを検索（フォールバック）"""
        results = []
        for incident in incidents:
            text = f"{incident.get('title', '')} {incident.get('description', '')}"
            score = self.keyword_search_score(query, text)
            if score > 0:
                results.append({**incident, "similarity_score": score})
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:10]


semantic_search_service = SemanticSearchService()
