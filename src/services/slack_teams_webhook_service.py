"""Slack/Teams Webhook通知サービス（設定DB対応・リトライ・イベント配信）"""

import asyncio
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def send_slack_message(url: str, payload: dict[str, Any]) -> bool:
    """Slack Incoming Webhook に Block Kit フォーマットで送信"""
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception:
        return False


async def send_teams_message(url: str, payload: dict[str, Any]) -> bool:
    """Microsoft Teams Incoming Webhook に Adaptive Card フォーマットで送信"""
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code in (200, 204)
    except Exception:
        return False


async def send_webhook_with_retry(
    config: Any,
    event_type: str,
    data: dict[str, Any],
    max_retries: int = 3,
) -> bool:
    """指数バックオフリトライ付きWebhook送信

    config: WebhookConfig ORM オブジェクト
    event_type: イベント種別 (e.g. "incident_created")
    data: 送信するペイロードデータ
    max_retries: 最大リトライ回数
    """
    webhook_type = config.webhook_type
    url = config.url

    if webhook_type == "slack":
        title = data.get("title", event_type)
        text = f"*{title}*\n{data.get('description', '')}"
        payload: dict[str, Any] = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": title[:150]},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*イベント:* {event_type}"},
                        {"type": "mrkdwn", "text": f"*優先度:* {data.get('priority', 'N/A')}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text},
                },
            ]
        }
        send_fn = send_slack_message
    else:
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": event_type,
            "themeColor": "0078D7",
            "sections": [
                {
                    "activityTitle": data.get("title", event_type),
                    "activityText": data.get("description", ""),
                    "facts": [
                        {"name": "イベント", "value": event_type},
                        {"name": "優先度", "value": data.get("priority", "N/A")},
                    ],
                }
            ],
        }
        send_fn = send_teams_message

    for attempt in range(max_retries):
        success = await send_fn(url, payload)
        if success:
            logger.info(
                "webhook_sent",
                webhook_id=config.id,
                event_type=event_type,
                attempt=attempt,
            )
            return True
        if attempt < max_retries - 1:
            await asyncio.sleep(2**attempt)

    logger.warning(
        "webhook_all_retries_failed",
        webhook_id=config.id,
        event_type=event_type,
        max_retries=max_retries,
    )
    return False


def _passes_filter(config: Any, event_type: str, data: dict[str, Any]) -> bool:
    """イベントフィルタ判定"""
    filters: dict[str, Any] = config.event_filters or {}

    # 優先度フィルタ
    allowed_priorities = filters.get("priorities")
    if allowed_priorities:
        priority = data.get("priority")
        if priority and priority not in allowed_priorities:
            return False

    # イベント種別フィルタ
    allowed_events = filters.get("events")
    if allowed_events:
        action = event_type.split("_")[-1]  # e.g. "incident_created" → "created"
        if action not in allowed_events and event_type not in allowed_events:
            return False

    return True


async def dispatch_incident_event(
    db: AsyncSession,
    event_type: str,
    incident: Any,
) -> None:
    """インシデントイベントをアクティブなWebhook設定へ配信"""
    from src.models.webhook import WebhookConfig

    result = await db.execute(select(WebhookConfig).where(WebhookConfig.is_active.is_(True)))
    configs = result.scalars().all()

    data = {
        "title": getattr(incident, "title", ""),
        "description": getattr(incident, "description", ""),
        "priority": getattr(incident, "priority", ""),
        "status": getattr(incident, "status", ""),
        "incident_number": getattr(incident, "incident_number", ""),
    }

    for config in configs:
        if _passes_filter(config, event_type, data):
            await send_webhook_with_retry(config, event_type, data, max_retries=config.retry_count)


async def dispatch_change_event(
    db: AsyncSession,
    event_type: str,
    change: Any,
) -> None:
    """変更管理イベントをアクティブなWebhook設定へ配信"""
    from src.models.webhook import WebhookConfig

    result = await db.execute(select(WebhookConfig).where(WebhookConfig.is_active.is_(True)))
    configs = result.scalars().all()

    data = {
        "title": getattr(change, "title", ""),
        "description": getattr(change, "description", ""),
        "priority": getattr(change, "priority", ""),
        "status": getattr(change, "status", ""),
        "change_number": getattr(change, "change_number", ""),
    }

    for config in configs:
        if _passes_filter(config, event_type, data):
            await send_webhook_with_retry(config, event_type, data, max_retries=config.retry_count)
