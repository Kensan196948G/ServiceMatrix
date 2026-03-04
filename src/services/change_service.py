"""変更管理ビジネスロジック - リスクスコアリング・CAB承認フロー"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.metrics import metrics
from src.models.change import Change

logger = get_logger(__name__)

# リスクスコアリングマトリクス
IMPACT_SCORES: dict[str, int] = {"Low": 10, "Medium": 30, "High": 50}
URGENCY_SCORES: dict[str, int] = {"Low": 5, "Medium": 15, "High": 30}
CHANGE_TYPE_SCORES: dict[str, int] = {"Standard": 0, "Normal": 10, "Emergency": 30, "Major": 20}

# リスクレベル判定
RISK_THRESHOLDS = [
    (70, "Critical"),
    (50, "High"),
    (30, "Medium"),
    (0, "Low"),
]

# 有効なステータス遷移
VALID_CHANGE_TRANSITIONS: dict[str, set[str]] = {
    "Draft": {"Submitted", "Cancelled"},
    "Submitted": {"CAB_Review", "Rejected", "Cancelled"},
    "CAB_Review": {"Approved", "Rejected"},
    "Approved": {"Scheduled", "Cancelled"},
    "Rejected": {"Draft"},
    "Scheduled": {"In_Progress", "Cancelled"},
    "In_Progress": {"Completed", "Failed"},
    "Completed": set(),
    "Cancelled": set(),
    "Failed": {"Draft"},
}

# CAB承認が必要な変更タイプ
CAB_REQUIRED_TYPES = {"Normal", "Emergency", "Major"}


async def _get_next_change_number(db: AsyncSession) -> str:
    """CHG-YYYY-NNNNNN形式の変更番号を生成"""
    year = datetime.now(UTC).year
    result = await db.execute(select(func.nextval("change_seq")))
    seq = result.scalar_one()
    return f"CHG-{year}-{seq:06d}"


def calculate_risk_score(
    change_type: str,
    impact_level: str | None,
    urgency_level: str | None,
) -> tuple[int, str]:
    """変更リスクスコアとリスクレベルを計算する"""
    score = (
        CHANGE_TYPE_SCORES.get(change_type, 10)
        + IMPACT_SCORES.get(impact_level or "Low", 10)
        + URGENCY_SCORES.get(urgency_level or "Low", 5)
    )
    score = min(score, 100)

    risk_level = "Low"
    for threshold, level in RISK_THRESHOLDS:
        if score >= threshold:
            risk_level = level
            break

    return score, risk_level


async def create_change(db: AsyncSession, data: dict[str, Any]) -> Change:
    """変更リクエストを作成し、リスクスコアを計算する"""
    change_number = await _get_next_change_number(db)
    risk_score, risk_level = calculate_risk_score(
        data.get("change_type", "Normal"),
        data.get("impact_level"),
        data.get("urgency_level"),
    )

    change = Change(
        change_number=change_number,
        risk_score=risk_score,
        risk_level=risk_level,
        created_at=datetime.now(UTC),
        **{k: v for k, v in data.items() if k not in ("created_at",)},
    )
    db.add(change)
    await db.flush()
    await db.refresh(change)
    logger.info("change_created", change_number=change_number, risk_score=risk_score)
    metrics.changes_created_total += 1
    return change


async def transition_change_status(db: AsyncSession, change: Change, new_status: str) -> Change:
    """変更ステータスを遷移させる"""
    allowed = VALID_CHANGE_TRANSITIONS.get(change.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"ステータス '{change.status}' から '{new_status}' への遷移は許可されていません。"
        )
    change.status = new_status
    now = datetime.now(UTC)
    if new_status == "In_Progress":
        change.actual_start_at = now
    elif new_status in {"Completed", "Failed"}:
        change.actual_end_at = now

    await db.flush()
    await db.refresh(change)
    return change


async def approve_by_cab(
    db: AsyncSession, change: Change, approver_id: uuid.UUID, approved: bool, notes: str | None
) -> Change:
    """CAB承認処理"""
    if change.status != "CAB_Review":
        raise ValueError("CABレビュー状態のみ承認・却下可能です")

    change.cab_approved_by = approver_id if approved else None
    change.cab_reviewed_at = datetime.now(UTC)
    change.cab_notes = notes
    change.status = "Approved" if approved else "Rejected"

    await db.flush()
    await db.refresh(change)
    logger.info(
        "change_cab_decision",
        change_number=change.change_number,
        approved=approved,
        approver_id=str(approver_id),
    )
    return change
