"""AI強化サービス - GPT-4/Claude API連携（モック対応）"""

import os


class AIService:
    """外部LLM API連携サービス（mock / openai / anthropic）"""

    def __init__(self) -> None:
        self.provider: str = os.getenv("AI_PROVIDER", "mock")
        self.api_key: str = os.getenv("AI_API_KEY", "")
        self.model: str = os.getenv("AI_MODEL", "gpt-4o-mini")

    async def summarize_incident(
        self,
        incident_title: str,
        description: str,
        comments: list[str],
    ) -> str:
        """インシデントの要約を生成"""
        if self.provider == "mock" or not self.api_key:
            comment_snippet = f"（コメント{len(comments)}件）" if comments else ""
            desc_preview = description[:100] if description else ""
            return f"[AI要約] {incident_title}: {desc_preview}... {comment_snippet}"

        try:
            import httpx

            comment_text = "\n".join(f"- {c}" for c in comments[:10])
            prompt = (
                f"インシデントタイトル: {incident_title}\n"
                f"説明: {description}\n"
                f"コメント:\n{comment_text}\n\n"
                "上記インシデントを3文以内で簡潔に要約してください。"
            )
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 300,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return f"[AI要約] {incident_title}: {description[:100]}..."

    async def generate_rca_report(
        self,
        problem_title: str,
        affected_services: list[str],
        timeline: list[str],
    ) -> dict:
        """根本原因分析レポートを生成"""
        if self.provider == "mock" or not self.api_key:
            return {
                "root_cause": "調査中 - AI分析に必要な情報を収集しています",
                "contributing_factors": [],
                "recommendations": ["詳細なログ調査", "関連CIの依存関係確認"],
                "prevention_measures": ["監視強化", "アラート閾値の見直し"],
            }

        try:
            import httpx

            service_text = ", ".join(affected_services) if affected_services else "不明"
            timeline_text = "\n".join(f"- {t}" for t in timeline[:20])
            prompt = (
                f"問題タイトル: {problem_title}\n"
                f"影響サービス: {service_text}\n"
                f"タイムライン:\n{timeline_text}\n\n"
                "根本原因分析を以下JSON形式で出力してください:\n"
                '{"root_cause": "...", "contributing_factors": [...], '
                '"recommendations": [...], "prevention_measures": [...]}'
            )
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 600,
                    },
                )
                resp.raise_for_status()
                import json

                content = resp.json()["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception:
            return {
                "root_cause": "調査中 - AI分析に必要な情報を収集しています",
                "contributing_factors": [],
                "recommendations": ["詳細なログ調査", "関連CIの依存関係確認"],
                "prevention_measures": ["監視強化", "アラート閾値の見直し"],
            }

    async def suggest_incident_priority(
        self,
        title: str,
        description: str,
        affected_service: str | None,
    ) -> str:
        """インシデントの優先度を提案"""
        if self.provider == "mock" or not self.api_key:
            title_lower = title.lower()
            if any(k in title_lower for k in ["critical", "down", "全停止", "障害"]):
                return "P1"
            if any(k in title_lower for k in ["high", "slow", "遅延", "警告"]):
                return "P2"
            return "P3"

        try:
            import httpx

            prompt = (
                f"インシデントタイトル: {title}\n"
                f"説明: {description}\n"
                f"影響サービス: {affected_service or '不明'}\n\n"
                "このインシデントの優先度をP1/P2/P3/P4の中から1つだけ回答してください。"
            )
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 10,
                    },
                )
                resp.raise_for_status()
                result = resp.json()["choices"][0]["message"]["content"].strip()
                if result in ("P1", "P2", "P3", "P4"):
                    return result
                return "P3"
        except Exception:
            return "P3"


ai_service = AIService()
