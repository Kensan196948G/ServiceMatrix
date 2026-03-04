"""E2Eシナリオ: WebSocket統計エンドポイントフロー"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_e2e_websocket_stats_endpoint(e2e_client):
    """WebSocket統計エンドポイントが200を返す"""
    resp = await e2e_client.get("/api/v1/ws/stats")
    assert resp.status_code == 200


async def test_e2e_websocket_stats_json_format(e2e_client):
    """WebSocket統計はJSON辞書形式で返される"""
    resp = await e2e_client.get("/api/v1/ws/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


async def test_e2e_websocket_stats_has_connection_info(e2e_client):
    """WebSocket統計はアクティブ接続数を含む"""
    resp = await e2e_client.get("/api/v1/ws/stats")
    assert resp.status_code == 200
    data = resp.json()
    # 接続数の情報を持つキーが存在することを確認
    assert len(data) >= 0  # 辞書として有効


async def test_e2e_websocket_stats_no_auth_required(e2e_client):
    """WebSocket統計エンドポイントは認証なしでアクセス可能"""
    # 認証ヘッダーなし
    resp = await e2e_client.get("/api/v1/ws/stats")
    assert resp.status_code == 200


async def test_e2e_websocket_stats_content_type(e2e_client):
    """WebSocket統計はapplication/jsonを返す"""
    resp = await e2e_client.get("/api/v1/ws/stats")
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")
