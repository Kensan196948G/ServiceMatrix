"""問題管理 GraphQL リゾルバー"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.graphql.types.problem import ProblemType
from src.models.problem import Problem


def _to_gql(row: Problem) -> ProblemType:
    return ProblemType(
        id=row.problem_id,
        problem_number=row.problem_number,
        title=row.title,
        description=row.description,
        priority=row.priority,
        status=row.status,
        assigned_to=row.assigned_to,
        root_cause=row.root_cause,
        workaround=row.workaround,
        known_error=row.known_error,
        resolved_at=row.resolved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def resolve_problems(
    session: AsyncSession,
    status: str | None = None,
    known_error: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[ProblemType]:
    """問題一覧を取得（フィルタ・ページネーション対応）"""
    stmt = select(Problem).order_by(Problem.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Problem.status == status)
    if known_error is not None:
        stmt = stmt.where(Problem.known_error == known_error)
    result = await session.execute(stmt)
    return [_to_gql(row) for row in result.scalars().all()]


async def resolve_problem(session: AsyncSession, id: UUID) -> ProblemType | None:
    """問題単件取得"""
    result = await session.execute(select(Problem).where(Problem.problem_id == id))
    row = result.scalar_one_or_none()
    return _to_gql(row) if row else None
