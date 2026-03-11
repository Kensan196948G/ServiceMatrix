"""AIトリアージサービス - キーワードベース優先度・カテゴリ自動判定"""

import uuid as _uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.models.incident import Incident

logger = get_logger(__name__)


@dataclass
class AITriageResult:
    priority: str  # Critical/High/Medium/Low
    category: str  # Network/Database/Application/Security/Infrastructure/Unknown
    confidence: float  # 0.0-1.0
    reasoning: str


class TriageProvider(ABC):
    """トリアージプロバイダー抽象基底クラス"""

    @abstractmethod
    async def analyze(self, title: str, description: str | None) -> AITriageResult: ...


class KeywordTriageProvider(TriageProvider):
    """既存のキーワードベーストリアージ（デフォルト、LLMなしで動作）"""

    CRITICAL_KEYWORDS = ["down", "outage", "critical", "production", "障害", "停止", "緊急"]
    HIGH_KEYWORDS = ["error", "failed", "timeout", "エラー", "失敗", "遅延"]
    LOW_KEYWORDS = ["info", "inquiry", "question", "request", "情報", "問い合わせ", "確認"]

    SECURITY_KEYWORDS = ["security", "breach", "unauthorized", "exploit", "セキュリティ", "不正"]
    NETWORK_KEYWORDS = ["network", "connectivity", "dns", "firewall", "ネットワーク", "接続"]
    DB_KEYWORDS = ["database", "db", "sql", "query", "データベース", "クエリ"]
    INFRA_KEYWORDS = ["server", "cpu", "memory", "disk", "load", "サーバー", "メモリ", "ディスク"]

    async def analyze(self, title: str, description: str | None) -> AITriageResult:
        text = f"{title} {description or ''}".lower()
        priority, priority_confidence, priority_reason = self._determine_priority(text)
        category, category_reason = self._determine_category(text)
        reasoning = f"Priority: {priority_reason}. Category: {category_reason}."
        return AITriageResult(
            priority=priority,
            category=category,
            confidence=priority_confidence,
            reasoning=reasoning,
        )

    def _determine_priority(self, text: str) -> tuple[str, float, str]:
        if any(kw in text for kw in self.CRITICAL_KEYWORDS):
            matched = [kw for kw in self.CRITICAL_KEYWORDS if kw in text]
            return "Critical", 0.9, f"Critical keywords matched: {matched}"
        if any(kw in text for kw in self.HIGH_KEYWORDS):
            matched = [kw for kw in self.HIGH_KEYWORDS if kw in text]
            return "High", 0.8, f"High keywords matched: {matched}"
        if any(kw in text for kw in self.LOW_KEYWORDS):
            matched = [kw for kw in self.LOW_KEYWORDS if kw in text]
            return "Low", 0.7, f"Low keywords matched: {matched}"
        return "Medium", 0.5, "No priority keywords matched; defaulting to Medium"

    def _determine_category(self, text: str) -> tuple[str, str]:
        if any(kw in text for kw in self.SECURITY_KEYWORDS):
            matched = [kw for kw in self.SECURITY_KEYWORDS if kw in text]
            return "Security", f"Security keywords matched: {matched}"
        if any(kw in text for kw in self.NETWORK_KEYWORDS):
            matched = [kw for kw in self.NETWORK_KEYWORDS if kw in text]
            return "Network", f"Network keywords matched: {matched}"
        if any(kw in text for kw in self.DB_KEYWORDS):
            matched = [kw for kw in self.DB_KEYWORDS if kw in text]
            return "Database", f"Database keywords matched: {matched}"
        if any(kw in text for kw in self.INFRA_KEYWORDS):
            matched = [kw for kw in self.INFRA_KEYWORDS if kw in text]
            return "Infrastructure", f"Infrastructure keywords matched: {matched}"
        return "Unknown", "No category keywords matched"


_TRIAGE_PROMPT = (
    "Triage this IT incident. Title: {title}. Description: {description}.\n"
    "Respond ONLY in JSON: "
    '{{"priority": "Critical|High|Medium|Low", '
    '"category": "Network|Database|Application|Security|Infrastructure|Unknown", '
    '"confidence": 0.0-1.0, "reasoning": "string"}}'
)


class OpenAITriageProvider(TriageProvider):
    """OpenAI API使用トリアージ（openai_api_keyが設定されている場合に使用）"""

    def __init__(self, api_key: str, model: str, api_base: str = ""):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base

    async def analyze(self, title: str, description: str | None) -> AITriageResult:
        try:
            import json  # noqa: PLC0415

            import openai  # noqa: PLC0415

            client_kwargs: dict = {"api_key": self.api_key}
            if self.api_base:
                client_kwargs["base_url"] = self.api_base
            client = openai.AsyncOpenAI(**client_kwargs)

            prompt = _TRIAGE_PROMPT.format(title=title, description=description or "")
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content or "{}")
            return AITriageResult(
                priority=data.get("priority", "Medium"),
                category=data.get("category", "Unknown"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", "LLM triage"),
            )
        except ImportError:
            logger.warning("openai package not installed; falling back to keyword triage")
            return await KeywordTriageProvider().analyze(title, description)


class OllamaTriageProvider(TriageProvider):
    """Ollamaローカルモデル使用トリアージ（オンプレミスLLM・APIキー不要）"""

    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url
        self.model = model

    async def analyze(self, title: str, description: str | None) -> AITriageResult:
        try:
            import json  # noqa: PLC0415

            import openai  # noqa: PLC0415

            # Ollamaは空のapi_keyを受け付けるがrequiredなため"ollama"を渡す
            client = openai.AsyncOpenAI(api_key="ollama", base_url=self.base_url)
            prompt = _TRIAGE_PROMPT.format(title=title, description=description or "")

            # Ollamaはresponse_format未対応モデルがあるためplain textでリクエスト
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an IT incident triage assistant. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or "{}"
            # JSON抽出: モデルがMarkdownコードブロックで返す場合に対応
            if "```" in content:
                content = content.split("```")[1].lstrip("json").strip()
            data = json.loads(content)
            return AITriageResult(
                priority=data.get("priority", "Medium"),
                category=data.get("category", "Unknown"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", "Ollama LLM triage"),
            )
        except ImportError:
            logger.warning("openai package not installed; falling back to keyword triage")
            return await KeywordTriageProvider().analyze(title, description)
        except Exception as e:
            logger.warning("Ollama triage failed (%s); falling back to keyword triage", e)
            return await KeywordTriageProvider().analyze(title, description)


def get_triage_provider() -> TriageProvider:
    """設定に基づいてプロバイダーを返すファクトリ関数"""
    provider = settings.llm_provider
    if provider == "openai" and settings.openai_api_key:
        return OpenAITriageProvider(settings.openai_api_key, settings.llm_model)
    if provider == "azure_openai" and settings.openai_api_base:
        return OpenAITriageProvider(
            settings.openai_api_key, settings.llm_model, settings.openai_api_base
        )
    if provider == "ollama":
        base_url = settings.openai_api_base or OllamaTriageProvider.DEFAULT_BASE_URL
        return OllamaTriageProvider(base_url=base_url, model=settings.llm_model)
    return KeywordTriageProvider()


class AITriageService:
    """トリアージエンジン（プロバイダー経由でLLM/キーワード切り替え可能）"""

    async def triage(self, title: str, description: str | None) -> AITriageResult:
        """プロバイダー経由で優先度・カテゴリを判定する"""
        provider = get_triage_provider()
        return await provider.analyze(title, description)

    async def apply_triage_to_incident(self, db: AsyncSession, incident_id: str) -> AITriageResult:
        """インシデントを取得してトリアージ実行・結果を保存する"""
        result = await db.execute(
            select(Incident).where(
                Incident.incident_id == _uuid.UUID(incident_id)
                if isinstance(incident_id, str)
                else incident_id
            )
        )
        incident = result.scalar_one_or_none()
        if not incident:
            logger.warning("Incident %s not found for triage", incident_id)
            return AITriageResult(
                priority="Unknown",
                category="Unknown",
                confidence=0.0,
                reasoning="Incident not found",
            )

        triage_result = await self.triage(incident.title, incident.description)
        incident.ai_triage_notes = (
            f"[AI Triage] Priority={triage_result.priority} "
            f"Category={triage_result.category} "
            f"Confidence={triage_result.confidence:.2f}\n"
            f"{triage_result.reasoning}"
        )
        await db.flush()
        logger.info(
            "Triage applied to incident %s: %s/%s",
            incident_id,
            triage_result.priority,
            triage_result.category,
        )
        return triage_result

    async def find_similar_incidents(
        self, db: AsyncSession, title: str, description: str | None, limit: int = 5
    ) -> list[dict]:
        """TF-IDFベースで類似インシデントを検索する"""
        import re  # noqa: PLC0415

        def _normalize(text: str) -> list[str]:
            text = text.lower()
            text = re.sub(r"[^\w\s]", " ", text)
            return [w for w in text.split() if len(w) > 1]

        query_words = _normalize(f"{title} {description or ''}")
        if not query_words:
            return []
        query_counts: dict[str, int] = {}
        for w in query_words:
            query_counts[w] = query_counts.get(w, 0) + 1

        result = await db.execute(select(Incident).order_by(Incident.created_at.desc()).limit(200))
        incidents = result.scalars().all()

        scores: list[dict] = []
        for inc in incidents:
            doc_words = _normalize(f"{inc.title} {inc.description or ''}")
            if not doc_words:
                continue
            doc_counts: dict[str, int] = {}
            for w in doc_words:
                doc_counts[w] = doc_counts.get(w, 0) + 1

            common = sum(
                min(query_counts[w], doc_counts[w]) for w in query_counts if w in doc_counts
            )
            denom = (sum(v * v for v in query_counts.values()) ** 0.5) * (
                sum(v * v for v in doc_counts.values()) ** 0.5
            )
            similarity = common / denom if denom > 0 else 0.0
            if similarity > 0:
                scores.append(
                    {
                        "incident_id": str(inc.incident_id),
                        "incident_number": inc.incident_number,
                        "title": inc.title,
                        "similarity": round(similarity, 4),
                    }
                )

        scores.sort(key=lambda x: x["similarity"], reverse=True)
        return scores[:limit]


ai_triage_service = AITriageService()
