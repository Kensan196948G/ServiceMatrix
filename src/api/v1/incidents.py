"""インシデント管理API - CRUD + ステータス遷移 + SLA"""

import json
import uuid
from typing import Annotated

import pydantic
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.cache import cache_delete_pattern, cache_get, cache_set
from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.incident import Incident
from src.models.incident_comment import IncidentComment
from src.models.problem import Problem
from src.models.user import User, UserRole
from src.schemas.common import PaginatedResponse
from src.schemas.incident import (
    BulkIncidentResponse,
    BulkIncidentUpdate,
    IncidentBulkAssign,
    IncidentCommentCreate,
    IncidentCommentResponse,
    IncidentCreate,
    IncidentResponse,
    IncidentStatusTransition,
    IncidentUpdate,
)
from src.services import incident_service, slack_teams_webhook_service
from src.services.ai_triage_service import ai_triage_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get(
    "",
    response_model=PaginatedResponse[IncidentResponse],
    summary="インシデント一覧取得",
    description="フィルタ・ページネーション対応のインシデント一覧を返します。",
)
async def list_incidents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    department: str | None = Query(default=None),
):
    """インシデント一覧取得（ページネーション）"""
    cache_key = f"incidents:list:{page}:{size}:{status_filter}:{priority}:{department}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return json.loads(cached)

    query = select(Incident)
    if status_filter:
        query = query.where(Incident.status == status_filter)
    if priority:
        query = query.where(Incident.priority == priority)
    if department:
        query = query.where(Incident.department == department)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * size).limit(size).order_by(Incident.created_at.desc())
    result = await db.execute(query)
    items = [IncidentResponse.model_validate(item) for item in result.scalars().all()]

    response_data = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )
    await cache_set(cache_key, json.dumps(jsonable_encoder(response_data)), ttl=60)
    return response_data


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="インシデント作成",
    description="新規インシデントを作成します。SLA自動計算・優先度設定に対応。",
)
async def create_incident(
    data: IncidentCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
):
    """インシデント作成"""
    incident = await incident_service.create_incident(db, data.model_dump(exclude_none=True))
    background_tasks.add_task(
        ai_triage_service.apply_triage_to_incident, db, str(incident.incident_id)
    )
    background_tasks.add_task(
        slack_teams_webhook_service.dispatch_incident_event, db, "incident_created", incident
    )
    await cache_delete_pattern("incidents:list:*")
    return incident


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="インシデント詳細取得",
    description="指定されたIDのインシデント詳細を返します。",
)
async def get_incident(
    incident_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """インシデント詳細取得"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )
    return incident


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="インシデント更新",
    description="指定されたIDのインシデントを部分更新します。",
)
async def update_incident(
    incident_id: uuid.UUID,
    data: IncidentUpdate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
):
    """インシデント更新"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(incident, field, value)
    await db.flush()
    await db.refresh(incident)
    background_tasks.add_task(
        slack_teams_webhook_service.dispatch_incident_event, db, "incident_updated", incident
    )
    await cache_delete_pattern("incidents:list:*")
    return incident


@router.post(
    "/{incident_id}/transitions",
    response_model=IncidentResponse,
    summary="インシデントステータス遷移",
    description="インシデントのステータスをITILワークフローに従って遷移させます。",
)
async def transition_incident_status(
    incident_id: uuid.UUID,
    transition: IncidentStatusTransition,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
):
    """インシデントステータス遷移"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )

    try:
        incident = await incident_service.transition_status(
            db, incident, transition.new_status, str(current_user.user_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return incident


@router.post(
    "/{incident_id}/ai-triage",
    summary="AIトリアージ実行",
    description="指定インシデントに対してAIトリアージを手動実行し結果を返します。",
)
async def run_ai_triage(
    incident_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
                UserRole.VIEWER,
            )
        ),
    ],
) -> dict:
    """AIトリアージを手動実行して結果を返す"""
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )
    triage_result = await ai_triage_service.apply_triage_to_incident(db, str(incident_id))
    await db.flush()
    return {
        "incident_id": str(incident_id),
        "priority": triage_result.priority,
        "category": triage_result.category,
        "confidence": triage_result.confidence,
        "reasoning": triage_result.reasoning,
        "ai_triage_notes": incident.ai_triage_notes,
    }


@router.post(
    "/bulk-update",
    response_model=BulkIncidentResponse,
    summary="インシデント一括操作",
    description="複数インシデントをまとめてクローズ・担当者変更・優先度変更します。",
    tags=["incidents"],
)
async def bulk_update_incidents(
    body: BulkIncidentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
            )
        ),
    ],
) -> BulkIncidentResponse:
    """インシデント一括操作（クローズ・担当者変更・優先度変更）"""
    updated = 0
    failed: list[uuid.UUID] = []
    for iid in body.incident_ids:
        try:
            result = await db.execute(select(Incident).where(Incident.incident_id == iid))
            incident = result.scalar_one_or_none()
            if not incident:
                failed.append(iid)
                continue
            if body.action == "close":
                incident.status = "Closed"
            elif body.action == "assign" and body.assignee_id is not None:
                incident.assigned_to = body.assignee_id
            elif body.action == "set_priority" and body.priority is not None:
                incident.priority = body.priority
            else:
                failed.append(iid)
                continue
            await db.flush()
            updated += 1
        except Exception:
            failed.append(iid)
    return BulkIncidentResponse(updated_count=updated, failed_ids=failed)


@router.patch(
    "/bulk/assign",
    summary="インシデント一括担当者割り当て",
    description="複数のインシデントに対して一括で担当者・担当チームを割り当てます。",
)
async def bulk_assign_incidents(
    data: IncidentBulkAssign,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
) -> dict:
    """インシデント一括担当者割り当て"""
    updated_ids = []
    for incident_id in data.incident_ids:
        result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            if data.assigned_to is not None:
                incident.assigned_to = data.assigned_to
            if data.assigned_team_id is not None:
                incident.assigned_team_id = data.assigned_team_id
            await db.flush()
            updated_ids.append(str(incident_id))
    return {"updated": len(updated_ids), "incident_ids": updated_ids}


@router.get(
    "/{incident_id}/comments",
    response_model=list[IncidentCommentResponse],
    summary="インシデントコメント一覧取得",
)
async def list_comments(
    incident_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[IncidentCommentResponse]:
    """インシデントのコメント一覧をcreated_at昇順で返す"""
    result = await db.execute(
        select(IncidentComment)
        .where(IncidentComment.incident_id == incident_id)
        .options(joinedload(IncidentComment.author))
        .order_by(IncidentComment.created_at.asc())
    )
    comments = result.scalars().all()
    return [
        IncidentCommentResponse(
            comment_id=c.comment_id,
            incident_id=c.incident_id,
            author_id=c.author_id,
            author_username=c.author.username,
            body=c.body,
            attachment_url=c.attachment_url,
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.post(
    "/{incident_id}/comments",
    response_model=IncidentCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="インシデントコメント投稿",
)
async def create_comment(
    incident_id: uuid.UUID,
    data: IncidentCommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IncidentCommentResponse:
    """インシデントにコメントを投稿する"""
    inc_result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    if not inc_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )
    comment = IncidentComment(
        incident_id=incident_id,
        author_id=current_user.user_id,
        body=data.body,
        attachment_url=data.attachment_url,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return IncidentCommentResponse(
        comment_id=comment.comment_id,
        incident_id=comment.incident_id,
        author_id=comment.author_id,
        author_username=current_user.username,
        body=comment.body,
        attachment_url=comment.attachment_url,
        created_at=comment.created_at,
    )


@router.delete(
    "/{incident_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="インシデントコメント削除",
)
async def delete_comment(
    incident_id: uuid.UUID,
    comment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """自分のコメントを削除する（SYSTEM_ADMINは全削除可）"""
    result = await db.execute(
        select(IncidentComment)
        .where(IncidentComment.comment_id == comment_id)
        .where(IncidentComment.incident_id == incident_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="コメントが見つかりません"
        )
    if comment.author_id != current_user.user_id and current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="このコメントを削除する権限がありません"
        )
    await db.delete(comment)
    await db.flush()


class LinkProblemRequest(pydantic.BaseModel):
    problem_id: uuid.UUID
    note: str | None = None


@router.post(
    "/{incident_id}/link-problem",
    summary="インシデントに問題をリンク",
    description="インシデントに既存の問題（Problem）をリンクします。",
)
async def link_problem(
    incident_id: uuid.UUID,
    body: LinkProblemRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SYSTEM_ADMIN,
                UserRole.SERVICE_MANAGER,
                UserRole.INCIDENT_MANAGER,
                UserRole.OPERATOR,
            )
        ),
    ],
) -> dict:
    """インシデントと問題を関連付ける"""
    inc_result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = inc_result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )

    prob_result = await db.execute(select(Problem).where(Problem.problem_id == body.problem_id))
    problem = prob_result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問題が見つかりません")

    incident.linked_problem_id = body.problem_id
    await db.flush()
    return {
        "linked": True,
        "problem_id": str(body.problem_id),
        "message": (
            f"インシデント {incident.incident_number} を問題 {problem.problem_number}"
            " にリンクしました"
        ),
    }


@router.get(
    "/{incident_id}/suggest-problem",
    summary="関連問題の提案",
    description="同一サービスを持つインシデントから関連する問題を提案します。",
)
async def suggest_problem(
    incident_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """AIリンク提案: 同一サービスの未解決インシデントに関連する問題を提案する"""
    inc_result = await db.execute(select(Incident).where(Incident.incident_id == incident_id))
    incident = inc_result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="インシデントが見つかりません"
        )
    prob_result = await db.execute(
        select(Problem).where(Problem.status.notin_(["Resolved", "Closed"]))
    )
    problems = prob_result.scalars().all()

    suggestions = []
    for problem in problems:
        score = 0.0
        # 同一サービスで類似スコア算出
        if incident.affected_service and problem.title:
            service = (incident.affected_service or "").lower()
            if service and service in problem.title.lower():
                score += 0.5
            if service and problem.description and service in problem.description.lower():
                score += 0.3
        # 同一優先度
        if incident.priority == problem.priority:
            score += 0.2
        if score > 0:
            suggestions.append(
                {
                    "problem_id": str(problem.problem_id),
                    "title": problem.title,
                    "similarity_score": round(score, 2),
                }
            )

    suggestions.sort(key=lambda x: float(x["similarity_score"]), reverse=True)  # type: ignore[arg-type]
    return {"suggestions": suggestions[:5]}
