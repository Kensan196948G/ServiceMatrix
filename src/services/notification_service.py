"""アラート通知サービス（GitHub Issues・Webhook）"""

import httpx
import structlog

from src.core.config import settings

logger = structlog.get_logger()


class NotificationService:
    """SLA違反時にGitHub IssuesおよびアウトバウンドWebhookで通知するサービス"""

    async def notify_sla_breach(
        self,
        incident_number: str,
        incident_title: str,
        priority: str,
        breach_type: str,  # "response" | "resolution"
    ) -> dict:
        """SLA違反通知を送信（GitHub Issue + Webhook）"""
        results = {}

        if settings.github_token and settings.github_repo:
            issue = await self._create_github_issue(
                incident_number, incident_title, priority, breach_type
            )
            results["github_issue"] = issue

        if settings.alert_webhook_enabled and settings.alert_webhook_url:
            webhook = await self._send_webhook(
                incident_number, incident_title, priority, breach_type
            )
            results["webhook"] = webhook

        return results

    async def _create_github_issue(
        self,
        incident_number: str,
        incident_title: str,
        priority: str,
        breach_type: str,
    ) -> dict | None:
        """GitHub REST API でIssueを作成"""
        title = f"[SLA違反] {incident_number}: {incident_title}"
        body = (
            f"## SLA違反検出\n\n"
            f"- **インシデント**: {incident_number}\n"
            f"- **タイトル**: {incident_title}\n"
            f"- **優先度**: {priority}\n"
            f"- **違反種別**: {breach_type}\n"
        )
        payload = {
            "title": title,
            "body": body,
            "labels": ["sla-breach", f"priority:{priority}"],
        }
        url = f"https://api.github.com/repos/{settings.github_repo}/issues"
        headers = {
            "Authorization": f"Bearer {settings.github_token}",  # noqa: S105
            "Accept": "application/vnd.github+json",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "github_issue_created",
                    issue_number=data.get("number"),
                    incident=incident_number,
                )
                return data
        except Exception as e:  # noqa: BLE001
            logger.warning("github_issue_creation_failed", error=str(e), incident=incident_number)
            return None

    async def _send_webhook(
        self,
        incident_number: str,
        incident_title: str,
        priority: str,
        breach_type: str,
    ) -> dict | None:
        """アウトバウンドWebhookにPOST送信（Slack/Teams互換）"""
        text = (
            f":rotating_light: *SLA違反検出*\n"
            f"インシデント: {incident_number} | {incident_title}\n"
            f"優先度: {priority} | 違反種別: {breach_type}"
        )
        payload = {
            "text": text,
            "incident_number": incident_number,
            "priority": priority,
            "breach_type": breach_type,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(settings.alert_webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info("webhook_sent", incident=incident_number)
                return {"status": "sent", "status_code": response.status_code}
        except Exception as e:  # noqa: BLE001
            logger.warning("webhook_send_failed", error=str(e), incident=incident_number)
            return None


notification_service = NotificationService()
