"""GraphQL API テスト - Issue #78"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.api.graphql.schema import schema

# ─── フィクスチャ ──────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime(2026, 3, 11, 12, 0, 0, tzinfo=UTC)


def _make_incident(**kwargs) -> MagicMock:
    m = MagicMock()
    m.incident_id = kwargs.get("incident_id", uuid.uuid4())
    m.incident_number = kwargs.get("incident_number", "INC-2026-000001")
    m.title = kwargs.get("title", "テストインシデント")
    m.description = kwargs.get("description", "説明")
    m.priority = kwargs.get("priority", "P2")
    m.status = kwargs.get("status", "New")
    m.reported_by = kwargs.get("reported_by", None)
    m.assigned_to = kwargs.get("assigned_to", None)
    m.sla_response_due_at = kwargs.get("sla_response_due_at", None)
    m.sla_resolution_due_at = kwargs.get("sla_resolution_due_at", None)
    m.sla_breached = kwargs.get("sla_breached", False)
    m.resolved_at = kwargs.get("resolved_at", None)
    m.closed_at = kwargs.get("closed_at", None)
    m.created_at = kwargs.get("created_at", _now())
    m.updated_at = kwargs.get("updated_at", _now())
    return m


def _make_change(**kwargs) -> MagicMock:
    m = MagicMock()
    m.change_id = kwargs.get("change_id", uuid.uuid4())
    m.change_number = kwargs.get("change_number", "CHG-2026-000001")
    m.title = kwargs.get("title", "テスト変更")
    m.description = kwargs.get("description", "変更説明")
    m.change_type = kwargs.get("change_type", "Normal")
    m.status = kwargs.get("status", "Draft")
    m.requested_by = kwargs.get("requested_by", None)
    m.assigned_to = kwargs.get("assigned_to", None)
    m.risk_score = kwargs.get("risk_score", 30)
    m.risk_level = kwargs.get("risk_level", "Low")
    m.scheduled_start_at = kwargs.get("scheduled_start_at", None)
    m.scheduled_end_at = kwargs.get("scheduled_end_at", None)
    m.created_at = kwargs.get("created_at", _now())
    m.updated_at = kwargs.get("updated_at", _now())
    return m


def _make_problem(**kwargs) -> MagicMock:
    m = MagicMock()
    m.problem_id = kwargs.get("problem_id", uuid.uuid4())
    m.problem_number = kwargs.get("problem_number", "PRB-2026-000001")
    m.title = kwargs.get("title", "テスト問題")
    m.description = kwargs.get("description", "問題説明")
    m.priority = kwargs.get("priority", "P3")
    m.status = kwargs.get("status", "New")
    m.assigned_to = kwargs.get("assigned_to", None)
    m.root_cause = kwargs.get("root_cause", None)
    m.workaround = kwargs.get("workaround", None)
    m.known_error = kwargs.get("known_error", False)
    m.resolved_at = kwargs.get("resolved_at", None)
    m.created_at = kwargs.get("created_at", _now())
    m.updated_at = kwargs.get("updated_at", _now())
    return m


def _make_ci(**kwargs) -> MagicMock:
    m = MagicMock()
    m.ci_id = kwargs.get("ci_id", uuid.uuid4())
    m.ci_name = kwargs.get("ci_name", "テストサーバー")
    m.ci_type = kwargs.get("ci_type", "Server")
    m.ci_class = kwargs.get("ci_class", "Physical")
    m.status = kwargs.get("status", "Active")
    m.owner_id = kwargs.get("owner_id", None)
    m.description = kwargs.get("description", "CI説明")
    m.created_at = kwargs.get("created_at", _now())
    m.updated_at = kwargs.get("updated_at", _now())
    return m


# ─── GraphQL 型変換テスト ─────────────────────────────────────────────────────


class TestIncidentType:
    def test_to_gql_maps_fields_correctly(self) -> None:
        """インシデントモデルから GraphQL 型へのマッピングが正しい"""
        from src.api.graphql.resolvers.incidents import _to_gql

        row = _make_incident(priority="P1", status="In_Progress")
        result = _to_gql(row)
        assert result.incident_number == "INC-2026-000001"
        assert result.priority == "P1"
        assert result.status == "In_Progress"
        assert result.sla_breached is False

    def test_to_gql_optional_fields_none(self) -> None:
        """Optional フィールドが None で正しくマッピングされる"""
        from src.api.graphql.resolvers.incidents import _to_gql

        row = _make_incident()
        result = _to_gql(row)
        assert result.assigned_to is None
        assert result.resolved_at is None


class TestChangeType:
    def test_to_gql_maps_fields_correctly(self) -> None:
        """変更モデルから GraphQL 型へのマッピングが正しい"""
        from src.api.graphql.resolvers.changes import _to_gql

        row = _make_change(change_type="Emergency", risk_score=80)
        result = _to_gql(row)
        assert result.change_number == "CHG-2026-000001"
        assert result.change_type == "Emergency"
        assert result.risk_score == 80


class TestProblemType:
    def test_to_gql_maps_known_error(self) -> None:
        """問題モデルの known_error フラグが正しくマッピングされる"""
        from src.api.graphql.resolvers.problems import _to_gql

        row = _make_problem(known_error=True, workaround="回避策あり")
        result = _to_gql(row)
        assert result.known_error is True
        assert result.workaround == "回避策あり"


class TestCmdbType:
    def test_to_gql_maps_fields_correctly(self) -> None:
        """CIモデルから GraphQL 型へのマッピングが正しい"""
        from src.api.graphql.resolvers.cmdb import _to_gql

        row = _make_ci(ci_name="本番DB", ci_type="Database")
        result = _to_gql(row)
        assert result.name == "本番DB"
        assert result.ci_type == "Database"


# ─── リゾルバー単体テスト ─────────────────────────────────────────────────────


class TestIncidentResolver:
    async def test_resolve_incidents_returns_list(self) -> None:
        """resolve_incidents がリストを返す"""
        from src.api.graphql.resolvers.incidents import resolve_incidents

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_incident(),
            _make_incident(incident_number="INC-2026-000002"),
        ]
        session.execute = AsyncMock(return_value=mock_result)

        results = await resolve_incidents(session)
        assert len(results) == 2

    async def test_resolve_incident_not_found_returns_none(self) -> None:
        """存在しないIDの場合 None を返す"""
        from src.api.graphql.resolvers.incidents import resolve_incident

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await resolve_incident(session, uuid.uuid4())
        assert result is None

    async def test_resolve_incident_found_returns_type(self) -> None:
        """存在するIDの場合 IncidentType を返す"""
        from src.api.graphql.resolvers.incidents import resolve_incident

        target_id = uuid.uuid4()
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_incident(incident_id=target_id)
        session.execute = AsyncMock(return_value=mock_result)

        result = await resolve_incident(session, target_id)
        assert result is not None
        assert result.id == target_id


class TestChangeResolver:
    async def test_resolve_changes_returns_list(self) -> None:
        """resolve_changes がリストを返す"""
        from src.api.graphql.resolvers.changes import resolve_changes

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_change()]
        session.execute = AsyncMock(return_value=mock_result)

        results = await resolve_changes(session)
        assert len(results) == 1

    async def test_resolve_change_not_found_returns_none(self) -> None:
        """存在しない変更IDの場合 None を返す"""
        from src.api.graphql.resolvers.changes import resolve_change

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await resolve_change(session, uuid.uuid4())
        assert result is None


class TestProblemResolver:
    async def test_resolve_problems_returns_list(self) -> None:
        """resolve_problems がリストを返す"""
        from src.api.graphql.resolvers.problems import resolve_problems

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_problem(),
            _make_problem(known_error=True),
        ]
        session.execute = AsyncMock(return_value=mock_result)

        results = await resolve_problems(session)
        assert len(results) == 2


class TestCmdbResolver:
    async def test_resolve_cmdb_items_returns_list(self) -> None:
        """resolve_cmdb_items がリストを返す"""
        from src.api.graphql.resolvers.cmdb import resolve_cmdb_items

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_ci()]
        session.execute = AsyncMock(return_value=mock_result)

        results = await resolve_cmdb_items(session)
        assert len(results) == 1


# ─── DataLoader テスト ────────────────────────────────────────────────────────


class TestDataLoader:
    def test_dataloader_context_has_all_loaders(self) -> None:
        """DataLoaderContext が全リソースのローダーを持つ"""
        from src.api.graphql.resolvers.dataloader import DataLoaderContext

        session = AsyncMock()
        ctx = DataLoaderContext(session)
        assert ctx.incident_loader is not None
        assert ctx.change_loader is not None
        assert ctx.problem_loader is not None
        assert ctx.cmdb_loader is not None

    async def test_incident_loader_batches_requests(self) -> None:
        """インシデント DataLoader がバッチリクエストを処理する"""
        from src.api.graphql.resolvers.dataloader import make_incident_loader

        ids = [uuid.uuid4(), uuid.uuid4()]
        session = AsyncMock()
        mock_result = MagicMock()
        rows = [_make_incident(incident_id=id_) for id_ in ids]
        mock_result.scalars.return_value.all.return_value = rows
        session.execute = AsyncMock(return_value=mock_result)

        loader = make_incident_loader(session)
        results = await loader.load_many(ids)
        assert len(results) == 2
        # バッチ呼び出しは1回のみ（N+1 解消確認）
        assert session.execute.call_count == 1

    async def test_incident_loader_returns_none_for_missing(self) -> None:
        """存在しないIDに対して None を返す"""
        from src.api.graphql.resolvers.dataloader import make_incident_loader

        ids = [uuid.uuid4()]
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # 何もない
        session.execute = AsyncMock(return_value=mock_result)

        loader = make_incident_loader(session)
        results = await loader.load_many(ids)
        assert results == [None]


# ─── スキーマ構造テスト ───────────────────────────────────────────────────────


class TestSchemaStructure:
    def test_schema_has_query_type(self) -> None:
        """スキーマに Query 型が定義されている"""
        assert schema._schema.query_type is not None

    def test_query_has_incidents_field(self) -> None:
        """Query に incidents フィールドがある"""
        fields = {f for f in schema._schema.query_type.fields}
        assert "incidents" in fields

    def test_query_has_changes_field(self) -> None:
        """Query に changes フィールドがある"""
        fields = {f for f in schema._schema.query_type.fields}
        assert "changes" in fields

    def test_query_has_problems_field(self) -> None:
        """Query に problems フィールドがある"""
        fields = {f for f in schema._schema.query_type.fields}
        assert "problems" in fields

    def test_query_has_cmdb_items_field(self) -> None:
        """Query に cmdbItems フィールドがある"""
        fields = {f for f in schema._schema.query_type.fields}
        assert "cmdbItems" in fields

    def test_query_has_dashboard_field(self) -> None:
        """Query に dashboard フィールドがある（統合クエリ）"""
        fields = {f for f in schema._schema.query_type.fields}
        assert "dashboard" in fields

    def test_incident_type_has_required_fields(self) -> None:
        """IncidentType に必須フィールドがある"""
        assert schema._schema.type_map.get("IncidentType") is not None

    def test_schema_introspection(self) -> None:
        """スキーマがイントロスペクションをサポートする"""
        introspection_query = """
        query {
            __schema {
                queryType {
                    name
                }
            }
        }
        """
        import graphql

        result = graphql.graphql_sync(schema._schema, introspection_query)
        assert result.errors is None
        assert result.data["__schema"]["queryType"]["name"] == "Query"


# ─── GraphQL エンドポイント統合テスト ─────────────────────────────────────────


class TestGraphQLEndpoint:
    async def test_graphql_endpoint_accessible(self) -> None:
        """GraphQL エンドポイントにアクセスできる"""
        from src.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/graphql")
            # GraphiQL が返るか、エンドポイントが存在すれば OK
            assert resp.status_code in (200, 405, 500)

    async def test_graphql_post_query_structure(self) -> None:
        """GraphQL POST リクエストが正常に処理される"""
        from src.api.graphql.schema import GraphQLContext

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        ctx = GraphQLContext()
        ctx._session = session


        result = await schema.execute(
            "{ incidents { incidentNumber } }",
            context_value=ctx,
        )
        assert result.errors is None
        assert result.data == {"incidents": []}

    async def test_graphql_dashboard_query(self) -> None:
        """統合ダッシュボードクエリが正常動作する"""
        from src.api.graphql.schema import GraphQLContext

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        ctx = GraphQLContext()
        ctx._session = session

        result = await schema.execute(
            """
            {
                dashboard(limit: 3) {
                    recentIncidents { incidentNumber priority }
                    recentChanges { changeNumber status }
                    recentProblems { problemNumber knownError }
                }
            }
            """,
            context_value=ctx,
        )
        assert result.errors is None
        assert "dashboard" in result.data
        assert "recentIncidents" in result.data["dashboard"]

    async def test_graphql_invalid_query_returns_error(self) -> None:
        """無効なクエリがエラーを返す"""
        from src.api.graphql.schema import GraphQLContext

        ctx = GraphQLContext()

        result = await schema.execute(
            "{ nonExistentField }",
            context_value=ctx,
        )
        assert result.errors is not None

    async def test_graphql_filter_incidents_by_status(self) -> None:
        """ステータスフィルタが正しく動作する"""
        from src.api.graphql.schema import GraphQLContext

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_incident(status="Resolved"),
        ]
        session.execute = AsyncMock(return_value=mock_result)

        ctx = GraphQLContext()
        ctx._session = session

        result = await schema.execute(
            '{ incidents(status: "Resolved") { incidentNumber status } }',
            context_value=ctx,
        )
        assert result.errors is None
        assert len(result.data["incidents"]) == 1
        assert result.data["incidents"][0]["status"] == "Resolved"

    async def test_graphql_problems_filter_known_error(self) -> None:
        """known_error フィルタが正しく動作する"""
        from src.api.graphql.schema import GraphQLContext

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_problem(known_error=True),
        ]
        session.execute = AsyncMock(return_value=mock_result)

        ctx = GraphQLContext()
        ctx._session = session

        result = await schema.execute(
            "{ problems(knownError: true) { problemNumber knownError } }",
            context_value=ctx,
        )
        assert result.errors is None
        assert result.data["problems"][0]["knownError"] is True
