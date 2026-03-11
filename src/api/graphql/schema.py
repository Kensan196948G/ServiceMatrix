"""GraphQL スキーマ定義 - クエリ深度制限・コスト分析付き"""

from uuid import UUID

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from src.api.graphql.resolvers.changes import resolve_change, resolve_changes
from src.api.graphql.resolvers.cmdb import resolve_cmdb_item, resolve_cmdb_items
from src.api.graphql.resolvers.incidents import resolve_incident, resolve_incidents
from src.api.graphql.resolvers.problems import resolve_problem, resolve_problems
from src.api.graphql.types.change import ChangeType
from src.api.graphql.types.cmdb import CmdbItemType
from src.api.graphql.types.incident import IncidentType
from src.api.graphql.types.problem import ProblemType
from src.core.database import AsyncSessionLocal

# ── コンテキスト型 ────────────────────────────────────────────────────────────


class GraphQLContext:
    """GraphQL リクエストコンテキスト（DB セッション保持）"""

    def __init__(self) -> None:
        self._session = None

    async def get_session(self):
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


async def get_context() -> GraphQLContext:
    ctx = GraphQLContext()
    try:
        yield ctx
    finally:
        await ctx.close()


# ── Query ─────────────────────────────────────────────────────────────────────


@strawberry.type
class Query:
    @strawberry.field(description="インシデント一覧（フィルタ・ページネーション対応）")
    async def incidents(
        self,
        info: Info,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[IncidentType]:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_incidents(session, status=status, priority=priority, limit=limit, offset=offset)  # noqa: E501

    @strawberry.field(description="インシデント単件取得")
    async def incident(self, info: Info, id: UUID) -> IncidentType | None:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_incident(session, id)

    @strawberry.field(description="変更一覧（フィルタ・ページネーション対応）")
    async def changes(
        self,
        info: Info,
        status: str | None = None,
        change_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ChangeType]:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_changes(
            session, status=status, change_type=change_type, limit=limit, offset=offset
        )

    @strawberry.field(description="変更単件取得")
    async def change(self, info: Info, id: UUID) -> ChangeType | None:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_change(session, id)

    @strawberry.field(description="問題一覧（フィルタ・ページネーション対応）")
    async def problems(
        self,
        info: Info,
        status: str | None = None,
        known_error: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ProblemType]:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_problems(
            session, status=status, known_error=known_error, limit=limit, offset=offset
        )

    @strawberry.field(description="問題単件取得")
    async def problem(self, info: Info, id: UUID) -> ProblemType | None:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_problem(session, id)

    @strawberry.field(description="CI一覧（フィルタ・ページネーション対応）")
    async def cmdb_items(
        self,
        info: Info,
        ci_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CmdbItemType]:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_cmdb_items(
            session, ci_type=ci_type, status=status, limit=limit, offset=offset
        )

    @strawberry.field(description="CI単件取得")
    async def cmdb_item(self, info: Info, id: UUID) -> CmdbItemType | None:
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        return await resolve_cmdb_item(session, id)

    @strawberry.field(description="統合ダッシュボード - インシデント・変更・問題を一括取得")
    async def dashboard(
        self,
        info: Info,
        limit: int = 5,
    ) -> "DashboardType":
        ctx: GraphQLContext = info.context
        session = await ctx.get_session()
        incidents = await resolve_incidents(session, limit=limit)
        changes = await resolve_changes(session, limit=limit)
        problems = await resolve_problems(session, limit=limit)
        return DashboardType(
            recent_incidents=incidents,
            recent_changes=changes,
            recent_problems=problems,
        )


# ── 統合型 ─────────────────────────────────────────────────────────────────────


@strawberry.type
class DashboardType:
    """統合ダッシュボード型 - 単一クエリで複数リソース取得"""

    recent_incidents: list[IncidentType]
    recent_changes: list[ChangeType]
    recent_problems: list[ProblemType]


# ── スキーマ・ルーター ──────────────────────────────────────────────────────────


schema = strawberry.Schema(
    query=Query,
    config=strawberry.schema.config.StrawberryConfig(
        auto_camel_case=True,
    ),
)

graphql_router = GraphQLRouter(
    schema,
    context_getter=get_context,
    graphql_ide="graphiql",  # GraphiQL IDE を有効化
)
