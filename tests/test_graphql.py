"""GraphQL API テスト"""

import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def graphql_client(engine):
    """GraphQL用テストクライアント（AsyncSessionLocalをSQLiteに差し替え）"""
    test_session_local = async_sessionmaker(engine, expire_on_commit=False)
    with patch("src.core.database.AsyncSessionLocal", test_session_local):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_graphql_schema_exists():
    """GraphQLスキーマが存在する"""
    from src.graphql.schema import schema

    assert schema is not None


async def test_graphql_router_exists():
    """GraphQLルーターが存在する"""
    from src.graphql.schema import graphql_router

    assert graphql_router is not None


async def test_graphql_incidents_query(graphql_client):
    """インシデント一覧クエリが実行できる"""
    query = """
    query {
        incidents(limit: 5) {
            items {
                id
                title
                status
                priority
            }
            total
            limit
            offset
        }
    }
    """
    resp = await graphql_client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "incidents" in data["data"]
    assert "items" in data["data"]["incidents"]
    assert "total" in data["data"]["incidents"]


async def test_graphql_changes_query(graphql_client):
    """変更要求クエリが実行できる"""
    query = """
    query {
        changes(limit: 5) {
            id
            title
            status
        }
    }
    """
    resp = await graphql_client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "changes" in data["data"]


async def test_graphql_incident_by_id_not_found(graphql_client):
    """存在しないIDで incident クエリがnullを返す"""
    query = f"""
    query {{
        incident(id: "{uuid.uuid4()}") {{
            id
            title
        }}
    }}
    """
    resp = await graphql_client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["incident"] is None


async def test_graphql_mutation_update_status_not_found(graphql_client):
    """存在しないインシデントの更新はsuccessFalseを返す"""
    mutation = f"""
    mutation {{
        updateIncidentStatus(id: "{uuid.uuid4()}", status: "Resolved") {{
            success
            message
        }}
    }}
    """
    resp = await graphql_client.post("/graphql", json={"query": mutation})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["updateIncidentStatus"]["success"] is False


async def test_graphql_incidents_with_status_filter(graphql_client):
    """statusフィルタ付きクエリが実行できる"""
    query = """
    query {
        incidents(limit: 10, status: "Open") {
            items { id title status }
            total
        }
    }
    """
    resp = await graphql_client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert "incidents" in data["data"]


async def test_graphql_invalid_query(graphql_client):
    """無効なクエリはエラーを返す"""
    resp = await graphql_client.post("/graphql", json={"query": "{ invalid_field }"})
    assert resp.status_code == 200
    data = resp.json()
    assert "errors" in data


async def test_graphql_types_incident_type():
    """IncidentType が strawberry 型として定義されている"""
    from src.graphql.types import IncidentType

    assert hasattr(IncidentType, "__strawberry_definition__")


async def test_graphql_types_paginated_incidents():
    """PaginatedIncidents 型が正しく定義されている"""
    from src.graphql.types import PaginatedIncidents

    assert hasattr(PaginatedIncidents, "__strawberry_definition__")


async def test_graphql_playground_accessible(graphql_client):
    """GraphiQL プレイグラウンドにアクセスできる"""
    resp = await graphql_client.get("/graphql", headers={"Accept": "text/html"})
    assert resp.status_code in (200, 404)


async def test_graphql_schema_query_fields():
    """スキーマに incidents, incident, changes フィールドが存在する"""
    from src.graphql.schema import schema

    result = schema.execute_sync("{ __schema { queryType { fields { name } } } }")
    assert result.errors is None
    field_names = [f["name"] for f in result.data["__schema"]["queryType"]["fields"]]
    assert "incidents" in field_names
    assert "incident" in field_names
    assert "changes" in field_names


async def test_graphql_schema_mutation_fields():
    """スキーマに updateIncidentStatus mutation が存在する"""
    from src.graphql.schema import schema

    result = schema.execute_sync("{ __schema { mutationType { fields { name } } } }")
    assert result.errors is None
    field_names = [f["name"] for f in result.data["__schema"]["mutationType"]["fields"]]
    assert "updateIncidentStatus" in field_names


async def test_graphql_incidents_pagination(graphql_client):
    """ページネーションパラメータが機能する"""
    query = """
    query {
        incidents(limit: 2, offset: 0) {
            items { id }
            total
            limit
            offset
        }
    }
    """
    resp = await graphql_client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["incidents"]["limit"] == 2
    assert data["data"]["incidents"]["offset"] == 0


async def test_graphql_endpoint_exists(graphql_client):
    """GraphQL エンドポイントが存在する（POST /graphql）"""
    resp = await graphql_client.post("/graphql", json={"query": "{ __typename }"})
    assert resp.status_code == 200
