"""GitHub Webhook受信エンドポイント"""

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.services import webhook_service

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload_bytes = await request.body()
    event_type = request.headers.get("X-GitHub-Event", "")
    signature = request.headers.get("X-Hub-Signature-256", "")

    # HMAC-SHA256 署名検証
    if settings.github_webhook_secret:
        if not signature or not webhook_service.verify_webhook_signature(
            payload_bytes, signature, settings.github_webhook_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature"
            )
    else:
        logger.warning(
            "webhook_secret_not_configured",
            detail="GITHUB_WEBHOOK_SECRET が未設定のため署名検証をスキップしました",
        )

    try:
        payload = json.loads(payload_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc

    action = payload.get("action")
    logger.info("github_webhook_received", event_type=event_type, action=action)

    if event_type == "ping":
        result = await webhook_service.process_ping_event(payload)
    elif event_type == "issues":
        result = await webhook_service.process_issues_event(db, payload)
    elif event_type == "pull_request":
        result = await webhook_service.process_pull_request_event(db, payload)
    else:
        return {"status": "ignored", "event": event_type}

    if result is None:
        return {"status": "no_action"}
    return result


@router.post("/github/advanced")
async def github_webhook_advanced(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """強化版Webhookエンドポイント - ラベルベースの自動連携"""
    payload_bytes = await request.body()
    event_type = request.headers.get("X-GitHub-Event", "")
    signature = request.headers.get("X-Hub-Signature-256", "")

    # HMAC-SHA256 署名検証
    if settings.github_webhook_secret:
        if not signature or not webhook_service.verify_webhook_signature(
            payload_bytes, signature, settings.github_webhook_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature"
            )
    else:
        logger.warning(
            "webhook_secret_not_configured",
            detail="GITHUB_WEBHOOK_SECRET が未設定のため署名検証をスキップしました",
        )

    try:
        payload = json.loads(payload_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc

    action = payload.get("action")
    logger.info("github_webhook_advanced_received", event_type=event_type, action=action)

    if event_type == "ping":
        return await webhook_service.process_ping_event(payload)
    elif event_type == "issues":
        return await webhook_service.process_issue_event(payload, db)
    elif event_type == "pull_request":
        return await webhook_service.process_pr_event(payload, db)
    else:
        return {"status": "ignored", "event": event_type}
