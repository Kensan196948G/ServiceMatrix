"""問題管理ビジネスロジック - Known Error DB・ステータス遷移"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from src.models.problem import Problem
from src.core.logging import get_logger

logger = get_logger(__name__)

# 有効なステータス遷移
VALID_PROBLEM_TRANSITIONS: dict[str, set[str]] = {
    "New": {"Under_Investigation", "Closed"},
    "Under_Investigation": {"Known_Error", "Resolved", "Closed"},
    "Known_Error": {"Resolved", "Under_Investigation"},
    "Resolved": {"Closed", "Under_Investigation"},
    "Closed": set(),
}


async def _get_next_problem_number(db: AsyncSession) -> str:
    """PRB-YYYY-NNNNNN形式の問題番号を生成"""
    year = datetime.now(timezone.utc).year
    result = await db.execute(select(func.nextval("problem_seq")))
    seq = result.scalar_one()
    return f"PRB-{year}-{seq:06d}"


async def create_problem(db: AsyncSession, data: dict[str, Any]) -> Problem:
    """問題レコードを作成する"""
    problem_number = await _get_next_problem_number(db)
    problem = Problem(
        problem_number=problem_number,
        created_at=datetime.now(timezone.utc),
        **{k: v for k, v in data.items() if k not in ("created_at",)},
    )
    db.add(problem)
    await db.flush()
    await db.refresh(problem)
    logger.info("problem_created", problem_number=problem_number, priority=problem.priority)
    return problem


async def transition_problem_status(
    db: AsyncSession, problem: Problem, new_status: str
) -> Problem:
    """問題ステータスを遷移させる"""
    allowed = VALID_PROBLEM_TRANSITIONS.get(problem.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"ステータス '{problem.status}' から '{new_status}' への遷移は許可されていません。"
            f"許可される遷移: {', '.join(allowed) or 'なし'}"
        )
    problem.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == "Resolved":
        problem.resolved_at = now
    elif new_status == "Closed":
        problem.closed_at = now
    await db.flush()
    await db.refresh(problem)
    logger.info("problem_status_changed", problem_number=problem.problem_number, new_status=new_status)
    return problem


async def mark_as_known_error(
    db: AsyncSession, problem: Problem, workaround: str
) -> Problem:
    """問題を既知エラーとしてマークし、ワークアラウンドを記録する"""
    if not workaround or not workaround.strip():
        raise ValueError("既知エラーにはワークアラウンドの記載が必須です")
    problem.known_error = True
    problem.workaround = workaround
    if problem.status not in ("Known_Error", "Resolved", "Closed"):
        problem.status = "Known_Error"
    await db.flush()
    await db.refresh(problem)
    logger.info("problem_known_error_set", problem_number=problem.problem_number)
    return problem
