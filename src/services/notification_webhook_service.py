"""Slack/Teams Webhook通知サービス"""

from typing import Literal

import httpx

WebhookType = Literal["slack", "teams"]


async def send_slack_notification(webhook_url: str, message: str, title: str = "") -> bool:
    """Slack Incoming Webhookに通知を送信"""
    if not webhook_url:
        return False
    text = f"*{title}*\n{message}" if title else message
    payload: dict = {"text": text}
    if title:
        payload["blocks"] = [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False


async def send_teams_notification(webhook_url: str, message: str, title: str = "") -> bool:
    """Microsoft Teams Incoming Webhookに通知を送信"""
    if not webhook_url:
        return False
    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": title or message,
        "themeColor": "0078D7",
        "sections": [{"activityTitle": title, "activityText": message}],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code in (200, 204)
    except Exception:  # noqa: BLE001
        return False


async def send_webhook_notification(
    webhook_url: str,
    webhook_type: WebhookType,
    message: str,
    title: str = "",
) -> bool:
    """WebhookタイプによりSlackまたはTeams通知を送信"""
    if webhook_type == "slack":
        return await send_slack_notification(webhook_url, message, title)
    elif webhook_type == "teams":
        return await send_teams_notification(webhook_url, message, title)
    return False
