"""E2Eシナリオ: AIワークフロー統合フロー"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_e2e_ai_triage_flow(e2e_client):
    """AIトリアージ統合フロー: Incident作成 → トリアージ実行 → 結果確認"""
    hdrs = e2e_client._e2e_headers

    # Incident作成
    create_resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: 本番DBサーバーダウン", "priority": "P2", "description": "CPU使用率が100%になり応答不能"},
        headers=hdrs,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    # AIトリアージ実行
    triage_resp = await e2e_client.post(
        f"/api/v1/ai/triage/{incident_id}",
        headers=hdrs,
    )
    assert triage_resp.status_code == 200
    data = triage_resp.json()
    assert data["incident_id"] == incident_id
    assert "priority" in data
    assert "category" in data
    assert "confidence" in data
    assert "reasoning" in data
    assert 0.0 <= data["confidence"] <= 1.0


async def test_e2e_ai_triage_not_found(e2e_client):
    """存在しないIncidentへのトリアージは404"""
    hdrs = e2e_client._e2e_headers

    import uuid
    resp = await e2e_client.post(
        f"/api/v1/ai/triage/{uuid.uuid4()}",
        headers=hdrs,
    )
    assert resp.status_code == 404


async def test_e2e_ai_similar_incidents_search(e2e_client):
    """類似インシデント検索統合テスト"""
    hdrs = e2e_client._e2e_headers

    # 複数のインシデントを作成しておく
    for title in ["E2E: ネットワーク障害A", "E2E: ネットワーク接続断B", "E2E: ディスク障害"]:
        await e2e_client.post(
            "/api/v1/incidents",
            json={"title": title, "priority": "P2"},
            headers=hdrs,
        )

    # 類似インシデント検索
    search_resp = await e2e_client.get(
        "/api/v1/ai/similar-incidents",
        params={"title": "ネットワーク障害", "limit": 5},
        headers=hdrs,
    )
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert isinstance(results, list)
    assert len(results) <= 5


async def test_e2e_ai_similar_incidents_with_description(e2e_client):
    """説明文付き類似インシデント検索"""
    hdrs = e2e_client._e2e_headers

    resp = await e2e_client.get(
        "/api/v1/ai/similar-incidents",
        params={
            "title": "サーバー障害",
            "description": "メモリ不足でプロセスがクラッシュ",
            "limit": 3,
        },
        headers=hdrs,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_e2e_ai_decision_log_recorded_after_triage(e2e_client):
    """トリアージ実行後にAI決定ログが記録される"""
    hdrs = e2e_client._e2e_headers

    # Incident作成
    create_resp = await e2e_client.post(
        "/api/v1/incidents",
        json={"title": "E2E: 決定ログ確認用インシデント", "priority": "P1"},
        headers=hdrs,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    # トリアージ実行
    await e2e_client.post(f"/api/v1/ai/triage/{incident_id}", headers=hdrs)

    # AI決定ログ確認
    log_resp = await e2e_client.get(
        "/api/v1/ai/decisions",
        params={"entity_id": incident_id, "action": "triage"},
        headers=hdrs,
    )
    assert log_resp.status_code == 200
    decisions = log_resp.json()
    assert isinstance(decisions, list)
    assert len(decisions) >= 1
    assert decisions[0]["action"] == "triage"
    assert decisions[0]["entity_id"] == incident_id


async def test_e2e_ai_decision_log_after_similar_search(e2e_client):
    """類似検索実行後にAI決定ログが記録される"""
    hdrs = e2e_client._e2e_headers

    # 類似検索実行
    await e2e_client.get(
        "/api/v1/ai/similar-incidents",
        params={"title": "E2E決定ログテスト"},
        headers=hdrs,
    )

    # 決定ログ一覧取得
    log_resp = await e2e_client.get(
        "/api/v1/ai/decisions",
        params={"action": "similar_search"},
        headers=hdrs,
    )
    assert log_resp.status_code == 200
    decisions = log_resp.json()
    assert isinstance(decisions, list)
    assert len(decisions) >= 1
    assert all(d["action"] == "similar_search" for d in decisions)


async def test_e2e_ai_decisions_summary(e2e_client):
    """AI決定サマリーAPIの確認"""
    hdrs = e2e_client._e2e_headers

    # サマリー取得
    resp = await e2e_client.get("/api/v1/ai/decisions/summary", headers=hdrs)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


async def test_e2e_ai_change_impact_analysis(e2e_client):
    """変更影響分析統合フロー: Change作成 → 影響分析 → 結果取得"""
    hdrs = e2e_client._e2e_headers

    # Change作成
    create_resp = await e2e_client.post(
        "/api/v1/changes",
        json={
            "title": "E2E: AI影響分析テスト変更",
            "change_type": "Normal",
            "impact_level": "High",
            "urgency_level": "Medium",
        },
        headers=hdrs,
    )
    assert create_resp.status_code == 201
    change_id = create_resp.json()["change_id"]

    # 影響分析実行
    impact_resp = await e2e_client.post(
        f"/api/v1/ai/change-impact/{change_id}",
        headers=hdrs,
    )
    assert impact_resp.status_code == 200
    data = impact_resp.json()
    assert data["change_id"] == change_id
    assert "risk_level" in data
    assert "risk_score" in data
    assert "recommendations" in data

    # 分析結果取得
    get_resp = await e2e_client.get(
        f"/api/v1/ai/change-impact/{change_id}",
        headers=hdrs,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["change_id"] == change_id
