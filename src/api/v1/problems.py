"""問題管理API - CRUD + ステータス遷移 + Known Error DB"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.problem import Problem
from src.models.user import User, UserRole
from src.schemas.common import PaginatedResponse
from src.schemas.problem import (
    KnownErrorUpdate, ProblemCreate, ProblemResponse,
    ProblemStatusTransition, ProblemUpdate
)
from src.services import problem_service

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("", response_model=PaginatedResponse[ProblemResponse])
async def list_problems(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    known_error: bool | None = Query(default=None),
):
    """問題一覧取得（ページネーション）"""
    query = select(Problem)
    if status_filter:
        query = query.where(Problem.status == status_filter)
    if priority:
        query = query.where(Problem.priority == priority)
    if known_error is not None:
        query = query.where(Problem.known_error == known_error)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * size).limit(size).order_by(Problem.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.post("", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    data: ProblemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.INCIDENT_MANAGER
    ))],
):
    """問題作成"""
    problem = await problem_service.create_problem(db, data.model_dump(exclude_none=True))
    return problem


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """問題詳細取得"""
    result = await db.execute(select(Problem).where(Problem.problem_id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問題が見つかりません")
    return problem


@router.patch("/{problem_id}", response_model=ProblemResponse)
async def update_problem(
    problem_id: uuid.UUID,
    data: ProblemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.INCIDENT_MANAGER
    ))],
):
    """問題更新"""
    result = await db.execute(select(Problem).where(Problem.problem_id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問題が見つかりません")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(problem, field, value)
    await db.flush()
    await db.refresh(problem)
    return problem


@router.post("/{problem_id}/transitions", response_model=ProblemResponse)
async def transition_problem_status(
    problem_id: uuid.UUID,
    transition: ProblemStatusTransition,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.INCIDENT_MANAGER
    ))],
):
    """問題ステータス遷移"""
    result = await db.execute(select(Problem).where(Problem.problem_id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問題が見つかりません")

    try:
        problem = await problem_service.transition_problem_status(
            db, problem, transition.new_status
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return problem


@router.post("/{problem_id}/known-error", response_model=ProblemResponse)
async def set_known_error(
    problem_id: uuid.UUID,
    data: KnownErrorUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(
        UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER, UserRole.INCIDENT_MANAGER
    ))],
):
    """既知エラー（Known Error DB）登録"""
    result = await db.execute(select(Problem).where(Problem.problem_id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問題が見つかりません")

    try:
        problem = await problem_service.mark_as_known_error(db, problem, data.workaround)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return problem
