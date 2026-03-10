"""GitHub Webhook イベント処理サービス"""

import hashlib
import hmac

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.incident import Incident
from src.services import incident_service

logger = structlog.get_logger()

GITHUB_ISSUE_PRIORITY_MAP = {
    "P1": "P1",
    "critical": "P1",
    "urgent": "P1",
    "P2": "P2",
    "high": "P2",
    "P3": "P3",
    "medium": "P3",
    "P4": "P4",
    "low": "P4",
}


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """GitHub署名検証（HMAC-SHA256）"""
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_issues_event(db: AsyncSession, payload: dict) -> dict | None:
    """GitHub Issuesイベント処理"""
    action = payload.get("action")
    issue = payload.get("issue", {})
    issue_number = issue.get("number")

    if action == "opened":
        labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
        priority = "P3"
        for label in labels:
            if label in GITHUB_ISSUE_PRIORITY_MAP:
                priority = GITHUB_ISSUE_PRIORITY_MAP[label]
                break

        title = f"[GitHub Issue #{issue_number}] {issue.get('title', '')}"
        description = issue.get("body") or ""

        incident = await incident_service.create_incident(
            db,
            {
                "title": title,
                "description": description,
                "priority": priority,
                "status": "open",
                "reported_by": "github-webhook",
            },
        )
        logger.info(
            "github_issue_incident_created",
            issue_number=issue_number,
            incident_id=str(incident.incident_id),
        )
        return {
            "incident_id": str(incident.incident_id),
            "incident_number": incident.incident_number,
        }

    if action == "closed":
        # GitHub Issueクローズ → 対応するIncidentをResolvedに更新
        result = await db.execute(
            select(Incident).where(Incident.github_issue_number == issue_number)
        )
        incident = result.scalar_one_or_none()
        if incident and incident.status not in ("Resolved", "Closed"):
            incident.status = "Resolved"
            await db.commit()
            logger.info("incident_resolved_via_github", issue_number=issue_number, incident_id=str(incident.incident_id))
            return {"action": "incident_resolved", "issue_number": issue_number, "incident_id": str(incident.incident_id)}
        return {"action": "issue_closed", "issue_number": issue_number}

    if action in ("labeled", "unlabeled"):
        # ラベル変更 → Incidentの優先度を同期
        result = await db.execute(
            select(Incident).where(Incident.github_issue_number == issue_number)
        )
        incident = result.scalar_one_or_none()
        if incident:
            labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
            for label in labels:
                if label in GITHUB_ISSUE_PRIORITY_MAP:
                    new_priority = GITHUB_ISSUE_PRIORITY_MAP[label]
                    if incident.priority != new_priority:
                        incident.priority = new_priority
                        await db.commit()
                        logger.info("incident_priority_synced", issue_number=issue_number, priority=new_priority)
                    return {"action": "priority_synced", "issue_number": issue_number, "priority": new_priority}
        return {"action": "label_changed", "issue_number": issue_number}

    if action in ("assigned", "unassigned"):
        return {"action": "assignment_changed", "issue_number": issue_number}

    return None


async def process_pull_request_event(db: AsyncSession, payload: dict) -> dict | None:
    """GitHub Pull Requestイベント処理"""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    title = pr.get("title", "")
    url = pr.get("html_url", "")

    if action == "opened":
        return {"action": "pr_opened", "pr_number": pr_number, "title": title, "url": url}

    if action == "closed" and pr.get("merged"):
        return {"action": "pr_merged", "pr_number": pr_number, "title": title}

    return None


async def process_ping_event(payload: dict) -> dict:
    """GitHub pingイベント処理"""
    return {
        "status": "pong",
        "hook_id": payload.get("hook_id"),
        "zen": payload.get("zen"),
    }
