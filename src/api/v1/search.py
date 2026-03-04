"""グローバル検索API - インシデント/問題/変更/CMDBをLIKE検索"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.change import Change
from src.models.cmdb import ConfigurationItem
from src.models.incident import Incident
from src.models.problem import Problem
from src.models.user import User

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", summary="グローバル検索")
async def global_search(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=2, description="検索キーワード（2文字以上）"),
    types: str | None = Query(default=None, description="カンマ区切りのリソースタイプ"),
    limit: int = Query(default=5, ge=1, le=50),
) -> dict[str, Any]:
    requested = set(types.split(",")) if types else {"incidents", "problems", "changes", "cmdb"}
    pattern = f"%{q}%"
    results: dict[str, list[dict[str, Any]]] = {}

    if "incidents" in requested:
        stmt = (
            select(Incident)
            .where(
                or_(
                    Incident.title.ilike(pattern),
                    Incident.description.ilike(pattern),
                )
            )
            .limit(limit)
        )
        rows = (await db.execute(stmt)).scalars().all()
        results["incidents"] = [
            {
                "id": str(r.incident_id),
                "title": r.title,
                "status": r.status,
                "type": "incident",
            }
            for r in rows
        ]

    if "problems" in requested:
        prob_stmt = (
            select(Problem)
            .where(
                or_(
                    Problem.title.ilike(pattern),
                    Problem.description.ilike(pattern),
                )
            )
            .limit(limit)
        )
        prob_rows = (await db.execute(prob_stmt)).scalars().all()
        results["problems"] = [
            {
                "id": str(r.problem_id),
                "title": r.title,
                "status": r.status,
                "type": "problem",
            }
            for r in prob_rows
        ]

    if "changes" in requested:
        chg_stmt = (
            select(Change)
            .where(
                or_(
                    Change.title.ilike(pattern),
                    Change.description.ilike(pattern),
                )
            )
            .limit(limit)
        )
        chg_rows = (await db.execute(chg_stmt)).scalars().all()
        results["changes"] = [
            {
                "id": str(r.change_id),
                "title": r.title,
                "status": r.status,
                "type": "change",
            }
            for r in chg_rows
        ]

    if "cmdb" in requested:
        ci_stmt = (
            select(ConfigurationItem)
            .where(
                or_(
                    ConfigurationItem.ci_name.ilike(pattern),
                    ConfigurationItem.description.ilike(pattern),
                )
            )
            .limit(limit)
        )
        ci_rows = (await db.execute(ci_stmt)).scalars().all()
        results["cmdb"] = [
            {
                "id": str(r.ci_id),
                "title": r.ci_name,
                "ci_type": r.ci_type,
                "type": "cmdb",
            }
            for r in ci_rows
        ]

    total = sum(len(v) for v in results.values())
    return {"query": q, "total": total, "results": results}
