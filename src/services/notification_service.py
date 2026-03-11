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

    def _github_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.github_token}",  # noqa: S105
            "Accept": "application/vnd.github+json",
        }

    async def create_incident_github_issue(
        self,
        incident_number: str,
        incident_title: str,
        priority: str,
        description: str = "",
    ) -> int | None:
        """インシデント作成時にGitHub Issueを自動生成し、Issue番号を返す"""
        if not (settings.github_token and settings.github_repo):
            return None
        priority_label_map = {"P1": "critical", "P2": "high", "P3": "medium", "P4": "low"}
        labels = [
            "servicematrix-incident",
            f"priority:{priority_label_map.get(priority, 'medium')}",
        ]
        payload = {
            "title": f"[{incident_number}] {incident_title}",
            "body": (
                f"## ServiceMatrix インシデント\n\n"
                f"- **番号**: {incident_number}\n"
                f"- **優先度**: {priority}\n\n"
                f"### 概要\n{description or '（説明なし）'}"
            ),
            "labels": labels,
        }
        url = f"https://api.github.com/repos/{settings.github_repo}/issues"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self._github_headers(), timeout=10
                )
                response.raise_for_status()
                data = response.json()
                issue_number: int = data["number"]
                logger.info(
                    "incident_github_issue_created",
                    issue_number=issue_number,
                    incident=incident_number,
                )
                return issue_number
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "incident_github_issue_creation_failed",
                error=str(e),
                incident=incident_number,
            )
            return None

    async def close_incident_github_issue(
        self,
        github_issue_number: int,
        incident_number: str,
    ) -> bool:
        """インシデント解決時にGitHub IssueをCloseする"""
        if not (settings.github_token and settings.github_repo):
            return False
        url = f"https://api.github.com/repos/{settings.github_repo}/issues/{github_issue_number}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url, json={"state": "closed"}, headers=self._github_headers(), timeout=10
                )
                response.raise_for_status()
                logger.info(
                    "incident_github_issue_closed",
                    issue_number=github_issue_number,
                    incident=incident_number,
                )
                return True
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "incident_github_issue_close_failed",
                error=str(e),
                incident=incident_number,
            )
            return False

    async def add_github_issue_comment(
        self,
        github_issue_number: int,
        comment: str,
        incident_number: str,
    ) -> bool:
        """GitHub IssueにコメントをPOSTする"""
        if not (settings.github_token and settings.github_repo):
            return False
        url = f"https://api.github.com/repos/{settings.github_repo}/issues/{github_issue_number}/comments"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json={"body": comment}, headers=self._github_headers(), timeout=10
                )
                response.raise_for_status()
                logger.info(
                    "github_issue_comment_added",
                    issue_number=github_issue_number,
                    incident=incident_number,
                )
                return True
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "github_issue_comment_failed",
                error=str(e),
                incident=incident_number,
            )
            return False

    async def _create_github_issue(
        self,
        incident_number: str,
        incident_title: str,
        priority: str,
        breach_type: str,
    ) -> dict | None:
        """GitHub REST API でSLA違反IssueまたはコメントをPOST"""
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
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self._github_headers(), timeout=10
                )
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

    async def notify_sla_warning(
        self,
        incident_number: str,
        incident_title: str,
        priority: str,
        warning_level: str,
        progress_percent: float,
    ) -> dict:
        """SLA事前警告通知を送信（Webhook経由）"""
        results = {}
        if settings.alert_webhook_enabled and settings.alert_webhook_url:
            emoji = ":warning:" if warning_level == "warning_70" else ":rotating_light:"
            text = (
                f"{emoji} *SLA警告 ({warning_level})*\n"
                f"インシデント: {incident_number} | {incident_title}\n"
                f"優先度: {priority} | 進捗: {progress_percent}%"
            )
            payload = {
                "text": text,
                "incident_number": incident_number,
                "priority": priority,
                "warning_level": warning_level,
                "progress_percent": progress_percent,
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        settings.alert_webhook_url, json=payload, timeout=10
                    )
                    response.raise_for_status()
                    logger.info(
                        "sla_warning_webhook_sent",
                        incident=incident_number,
                        level=warning_level,
                    )
                    results["webhook"] = {"status": "sent", "status_code": response.status_code}
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "sla_warning_webhook_failed",
                    error=str(e),
                    incident=incident_number,
                )
                results["webhook"] = None
        return results

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
