"""GitHub Webhook イベント処理サービス"""

import hashlib
import hmac

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.incident import Incident
from src.services import change_service, incident_service

logger = structlog.get_logger()

# GitHub Issue ラベル → インシデント優先度マッピング
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

# インシデント自動作成をトリガーするラベル
INCIDENT_TRIGGER_LABELS = {"incident", "urgent"}

# 変更要求自動作成をトリガーするラベル
CHANGE_REQUEST_TRIGGER_LABELS = {"change-request"}


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
            incident_id=str(incident.id),
        )
        return {"incident_id": str(incident.id), "incident_number": incident.incident_number}

    if action == "closed":
        return {"action": "issue_closed", "issue_number": issue_number}

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


# === 強化版イベント処理関数 ===


async def process_issue_event(payload: dict, db: AsyncSession) -> dict:
    """Issue→インシデント自動連携（ラベルフィルタリング付き）

    - action=="opened" かつ incident/urgent ラベル付きで自動インシデント作成
    - action=="closed" かつ対応インシデントが存在する場合は Resolved に更新
    """
    action = payload.get("action")
    issue = payload.get("issue", {})
    issue_number = issue.get("number")
    labels = {lbl.get("name", "") for lbl in issue.get("labels", [])}

    if action == "opened":
        # ラベルにincidentまたはurgentが含まれない場合はスキップ
        if not labels & INCIDENT_TRIGGER_LABELS:
            logger.info(
                "issue_event_skipped_no_trigger_label",
                issue_number=issue_number,
                labels=list(labels),
            )
            return {"status": "skipped", "reason": "no_trigger_label"}

        # 優先度をラベルから判定（デフォルトP3）
        priority = "P3"
        for label in labels:
            if label in GITHUB_ISSUE_PRIORITY_MAP:
                priority = GITHUB_ISSUE_PRIORITY_MAP[label]
                break

        title = f"[GH#{issue_number}] {issue.get('title', '')}"
        description = issue.get("body") or ""

        inc = await incident_service.create_incident(
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
            "issue_auto_incident_created",
            issue_number=issue_number,
            incident_id=str(inc.id),
        )
        return {
            "action": "incident_created",
            "incident_id": str(inc.id),
            "incident_number": inc.incident_number,
            "issue_number": issue_number,
        }

    if action == "closed":
        # [GH#<number>] パターンでインシデントを検索
        title_prefix = f"[GH#{issue_number}]"
        result = await db.execute(select(Incident).where(Incident.title.startswith(title_prefix)))
        incident = result.scalars().first()

        if incident and incident.status not in ("Resolved", "Closed"):
            incident.status = "Resolved"
            await db.flush()
            logger.info(
                "issue_auto_incident_resolved",
                issue_number=issue_number,
                incident_number=incident.incident_number,
            )
            return {
                "action": "incident_resolved",
                "incident_number": incident.incident_number,
                "issue_number": issue_number,
            }

        return {"action": "issue_closed", "issue_number": issue_number, "incident_found": False}

    return {"status": "ignored", "action": action}


async def process_pr_event(payload: dict, db: AsyncSession) -> dict:
    """PR→変更要求自動連携

    - action=="opened" かつ change-request ラベル付きで自動変更要求作成
    """
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    labels = {lbl.get("name", "") for lbl in pr.get("labels", [])}

    if action == "opened":
        # ラベルにchange-requestが含まれない場合はスキップ
        if not labels & CHANGE_REQUEST_TRIGGER_LABELS:
            logger.info(
                "pr_event_skipped_no_trigger_label",
                pr_number=pr_number,
                labels=list(labels),
            )
            return {"status": "skipped", "reason": "no_trigger_label"}

        title = f"[PR#{pr_number}] {pr.get('title', '')}"
        description = pr.get("body") or ""

        change = await change_service.create_change(
            db,
            {
                "title": title,
                "description": description,
                "change_type": "Normal",
                "status": "Draft",
            },
        )
        logger.info(
            "pr_auto_change_created",
            pr_number=pr_number,
            change_number=change.change_number,
        )
        return {
            "action": "change_created",
            "change_id": str(change.change_id),
            "change_number": change.change_number,
            "pr_number": pr_number,
        }

    return {"status": "ignored", "action": action}
