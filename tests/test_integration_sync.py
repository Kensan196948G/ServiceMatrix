"""統合同期サービステスト - Jira/ServiceNow双方向同期基盤 (Issue #56)"""

from unittest.mock import patch

import pytest
import pytest_asyncio

from src.services.integration_sync_service import IntegrationSyncService


@pytest_asyncio.fixture(autouse=True)
async def mock_incident_seq():
    """func.nextval('incident_seq') の代替（SQLite非対応のためモック）"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"INC-2024-{_counter[0]:06d}"

    with patch("src.services.incident_service._get_next_incident_number", _get_next):
        yield


# ---------------------------------------------------------------------------
# Unit tests: IntegrationSyncService
# ---------------------------------------------------------------------------


@pytest.fixture
def sync_service() -> IntegrationSyncService:
    return IntegrationSyncService()


@pytest.mark.asyncio
async def test_field_mapping_jira_outbound(sync_service: IntegrationSyncService) -> None:
    """Jira フィールドマッピング（アウトバウンド）"""
    source = {
        "title": "システム障害発生",
        "description": "本番環境でエラーが発生しています",
        "priority": "P1",
        "status": "Open",
    }
    result = sync_service.map_fields(source, "jira", "outbound")
    assert result["summary"] == "システム障害発生"
    assert result["description"] == "本番環境でエラーが発生しています"
    assert result["priority.name"] == "P1"
    assert result["status.name"] == "Open"


@pytest.mark.asyncio
async def test_field_mapping_servicenow_outbound(sync_service: IntegrationSyncService) -> None:
    """ServiceNow フィールドマッピング（アウトバウンド）"""
    source = {
        "title": "ネットワーク障害",
        "description": "ルーターが応答しない",
        "priority": "2",
        "status": "New",
    }
    result = sync_service.map_fields(source, "servicenow", "outbound")
    assert result["short_description"] == "ネットワーク障害"
    assert result["description"] == "ルーターが応答しない"
    assert result["priority"] == "2"
    assert result["state"] == "New"


@pytest.mark.asyncio
async def test_field_mapping_inbound(sync_service: IntegrationSyncService) -> None:
    """逆マッピング（受信時 - inbound）"""
    # Jira → ServiceMatrix のフィールドマッピング
    jira_data = {
        "summary": "Jira チケットタイトル",
        "description": "Jira の説明文",
    }
    result = sync_service.map_fields(jira_data, "jira", "inbound")
    assert result["title"] == "Jira チケットタイトル"
    assert result["description"] == "Jira の説明文"


@pytest.mark.asyncio
async def test_field_mapping_unknown_type(sync_service: IntegrationSyncService) -> None:
    """未知の統合タイプは空辞書を返す"""
    source = {"title": "テスト", "description": "テスト説明"}
    result = sync_service.map_fields(source, "unknown_system", "outbound")
    assert result == {}


@pytest.mark.asyncio
async def test_sync_incident_to_jira_mock(sync_service: IntegrationSyncService) -> None:
    """Jira同期モック - 成功ケース"""
    incident_data = {
        "incident_id": "abcd1234-5678-0000-0000-000000000000",
        "title": "本番DB接続エラー",
        "description": "データベースに接続できません",
        "priority": "P1",
        "status": "Open",
    }
    config = {"config_id": "test-config-001"}

    result = await sync_service.sync_incident_to_jira(incident_data, config)

    assert result["success"] is True
    assert "external_id" in result
    assert result["external_id"].startswith("SVCM-")
    assert "mapped_fields" in result
    assert result["mapped_fields"]["summary"] == "本番DB接続エラー"


@pytest.mark.asyncio
async def test_sync_incident_to_servicenow_mock(sync_service: IntegrationSyncService) -> None:
    """ServiceNow同期モック - 成功ケース"""
    incident_data = {
        "incident_id": "efgh5678-0000-0000-0000-000000000000",
        "title": "メール送信エラー",
        "description": "SMTPサーバーが応答しません",
        "priority": "3",
        "status": "New",
    }
    config = {"config_id": "test-config-002"}

    result = await sync_service.sync_incident_to_servicenow(incident_data, config)

    assert result["success"] is True
    assert "sys_id" in result
    assert result["sys_id"].startswith("SN-")
    assert "mapped_fields" in result
    assert result["mapped_fields"]["short_description"] == "メール送信エラー"


@pytest.mark.asyncio
async def test_test_connection_unknown_type(sync_service: IntegrationSyncService) -> None:
    """未知の統合タイプは失敗を返す"""
    result = await sync_service.test_connection(
        integration_type="unknown",
        base_url="https://example.com",
        api_key="test-key",
    )
    assert result["success"] is False
    assert "Unknown type" in result["error"]


@pytest.mark.asyncio
async def test_test_connection_network_error(sync_service: IntegrationSyncService) -> None:
    """ネットワークエラー時は success=False を返す"""
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        result = await sync_service.test_connection(
            integration_type="jira",
            base_url="https://unreachable.example.com",
            api_key="test-key",
        )
    assert result["success"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_configs_endpoint(client, auth_headers) -> None:
    """同期設定一覧エンドポイント"""
    resp = await client.get("/api/v1/integrations/sync/configs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for item in data:
        assert "config_id" in item
        assert "integration_type" in item
        assert "is_active" in item


@pytest.mark.asyncio
async def test_connection_test_endpoint(client, auth_headers) -> None:
    """接続テストエンドポイント - unknown typeは200でsuccess=False"""
    payload = {
        "integration_type": "unknown",
        "base_url": "https://example.com",
        "api_key": "dummy-key",
    }
    resp = await client.post(
        "/api/v1/integrations/sync/test-connection",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_sync_status_endpoint(client, auth_headers) -> None:
    """同期ステータスエンドポイント"""
    resp = await client.get("/api/v1/integrations/sync/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_synced" in data
    assert "pending_count" in data
    assert "failed_count" in data
    assert "integrations" in data
    assert isinstance(data["integrations"], list)


@pytest.mark.asyncio
async def test_sync_trigger_endpoint_jira(client, auth_headers) -> None:
    """手動同期トリガー - Jira（インシデント事前作成）"""
    # 事前にインシデントを作成して実際のIDを取得
    create_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Jira同期テスト", "priority": "P2"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    payload = {
        "config_id": "00000000-0000-0000-0000-000000000001",
        "incident_id": incident_id,
        "integration_type": "jira",
    }
    resp = await client.post(
        "/api/v1/integrations/sync/trigger",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "external_id" in data


@pytest.mark.asyncio
async def test_sync_trigger_endpoint_servicenow(client, auth_headers) -> None:
    """手動同期トリガー - ServiceNow（インシデント事前作成）"""
    # 事前にインシデントを作成して実際のIDを取得
    create_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "ServiceNow同期テスト", "priority": "P3"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    payload = {
        "config_id": "00000000-0000-0000-0000-000000000002",
        "incident_id": incident_id,
        "integration_type": "servicenow",
    }
    resp = await client.post(
        "/api/v1/integrations/sync/trigger",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "sys_id" in data


@pytest.mark.asyncio
async def test_sync_trigger_endpoint_invalid_type(client, auth_headers) -> None:
    """手動同期トリガー - 無効な統合タイプは400"""
    payload = {
        "config_id": "00000000-0000-0000-0000-000000000001",
        "incident_id": "abcd1234-0000-0000-0000-000000000000",
        "integration_type": "invalid_system",
    }
    resp = await client.post(
        "/api/v1/integrations/sync/trigger",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sync_endpoint_unauthorized(client) -> None:
    """認証なしはすべてのエンドポイントで401"""
    resp = await client.get("/api/v1/integrations/sync/configs")
    assert resp.status_code == 401
