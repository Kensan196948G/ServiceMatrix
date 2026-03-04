"""Strawberry GraphQL スキーマ定義"""

import uuid

import strawberry
from strawberry.fastapi import GraphQLRouter

from src.graphql.types import (
    ChangeRequestType,
    IncidentType,
    NotificationType,
    PaginatedIncidents,
)


def get_context():
    """GraphQL コンテキスト（DB セッションは各リゾルバーで取得）"""
    return {}


@strawberry.type
class Query:
    @strawberry.field(description="インシデント一覧取得")
    async def incidents(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> PaginatedIncidents:
        from sqlalchemy import func, select

        from src.core.database import AsyncSessionLocal
        from src.models.incident import Incident

        async with AsyncSessionLocal() as db:
            query = select(Incident).order_by(Incident.created_at.desc())
            count_query = select(func.count()).select_from(Incident)
            if status:
                query = query.where(Incident.status == status)
                count_query = count_query.where(Incident.status == status)

            count_result = await db.execute(count_query)
            total = count_result.scalar_one()

            result = await db.execute(query.limit(limit).offset(offset))
            incidents = result.scalars().all()

            items = [
                IncidentType(
                    id=inc.incident_id,
                    incident_number=inc.incident_number,
                    title=inc.title,
                    status=inc.status,
                    priority=inc.priority,
                    created_at=inc.created_at,
                    updated_at=inc.updated_at,
                )
                for inc in incidents
            ]
            return PaginatedIncidents(items=items, total=total, limit=limit, offset=offset)

    @strawberry.field(description="インシデント単件取得")
    async def incident(self, id: uuid.UUID) -> IncidentType | None:
        from sqlalchemy import select

        from src.core.database import AsyncSessionLocal
        from src.models.incident import Incident

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Incident).where(Incident.incident_id == id))
            inc = result.scalar_one_or_none()
            if not inc:
                return None
            return IncidentType(
                id=inc.incident_id,
                incident_number=inc.incident_number,
                title=inc.title,
                status=inc.status,
                priority=inc.priority,
                created_at=inc.created_at,
                updated_at=inc.updated_at,
            )

    @strawberry.field(description="変更要求一覧取得")
    async def changes(self, limit: int = 20, offset: int = 0) -> list[ChangeRequestType]:
        from sqlalchemy import select

        from src.core.database import AsyncSessionLocal
        from src.models.change import Change

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Change).order_by(Change.created_at.desc()).limit(limit).offset(offset)
            )
            changes = result.scalars().all()
            return [
                ChangeRequestType(
                    id=ch.change_id,
                    change_number=ch.change_number,
                    title=ch.title,
                    status=ch.status,
                    risk_score=ch.risk_score,
                    created_at=ch.created_at,
                )
                for ch in changes
            ]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="インシデントステータス更新")
    async def update_incident_status(
        self,
        id: uuid.UUID,
        status: str,
    ) -> NotificationType:
        from sqlalchemy import select

        from src.core.database import AsyncSessionLocal
        from src.models.incident import Incident

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Incident).where(Incident.incident_id == id))
            inc = result.scalar_one_or_none()
            if not inc:
                return NotificationType(success=False, message="インシデントが見つかりません")
            inc.status = status
            await db.commit()
            return NotificationType(success=True, message=f"ステータスを {status} に更新しました")


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, graphql_ide="graphiql")
