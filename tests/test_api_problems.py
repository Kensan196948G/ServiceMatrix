"""問題管理 API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def mock_problem_seq():
    """func.nextval('problem_seq') の代替（SQLite非対応のためモック）"""
    _counter = [0]

    async def _get_next(db):
        _counter[0] += 1
        return f"PRB-2024-{_counter[0]:06d}"

    with patch("src.services.problem_service._get_next_problem_number", _get_next):
        yield


# ─── 作成テスト ──────────────────────────────────────────────────────────────

async def test_create_problem(client, auth_headers):
    """POST /problems → 201, problem_number が PRB- プレフィックスを持つ"""
    resp = await client.post(
        "/api/v1/problems",
        json={"title": "DBパフォーマンス劣化問題", "priority": "P2"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["problem_number"].startswith("PRB-")
    assert data["title"] == "DBパフォーマンス劣化問題"
    assert data["status"] == "New"
    assert data["known_error"] is False


# ─── 詳細取得テスト ──────────────────────────────────────────────────────────

async def test_get_problem(client, auth_headers):
    """POST → GET /problems/{id} → 200, 同一データ確認"""
    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "取得テスト問題", "priority": "P3"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    problem_id = create_resp.json()["problem_id"]

    resp = await client.get(f"/api/v1/problems/{problem_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["problem_id"] == problem_id
    assert data["title"] == "取得テスト問題"


# ─── 一覧取得テスト ──────────────────────────────────────────────────────────

async def test_list_problems(client, auth_headers):
    """GET /problems → 200, ページネーション構造確認"""
    resp = await client.get("/api/v1/problems", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert isinstance(data["items"], list)


# ─── 更新テスト ──────────────────────────────────────────────────────────────

async def test_update_problem(client, auth_headers):
    """PATCH /problems/{id} → 200, フィールド更新確認"""
    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "更新テスト問題", "priority": "P3"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    problem_id = create_resp.json()["problem_id"]

    update_resp = await client.patch(
        f"/api/v1/problems/{problem_id}",
        json={"root_cause": "ディスクI/Oボトルネック", "priority": "P2"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["root_cause"] == "ディスクI/Oボトルネック"
    assert data["priority"] == "P2"


# ─── 既知エラー登録テスト ────────────────────────────────────────────────────

async def test_mark_known_error(client, auth_headers):
    """POST /problems/{id}/known-error → 200, known_error=True & workaround設定"""
    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "既知エラーテスト", "priority": "P3"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    problem_id = create_resp.json()["problem_id"]

    resp = await client.post(
        f"/api/v1/problems/{problem_id}/known-error",
        json={"workaround": "サービス再起動で一時回避可能"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["known_error"] is True
    assert data["workaround"] == "サービス再起動で一時回避可能"
    assert data["status"] == "Known_Error"


# ─── 404テスト ───────────────────────────────────────────────────────────────

async def test_problem_not_found(client, auth_headers):
    """存在しない UUID → 404"""
    resp = await client.get(f"/api/v1/problems/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ─── ステータス遷移テスト ────────────────────────────────────────────────────

async def test_transition_problem_status(client, auth_headers):
    """POST /problems/{id}/transitions → New → Under_Investigation"""
    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "遷移テスト問題", "priority": "P2"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    problem_id = create_resp.json()["problem_id"]

    trans_resp = await client.post(
        f"/api/v1/problems/{problem_id}/transitions",
        json={"new_status": "Under_Investigation"},
        headers=auth_headers,
    )
    assert trans_resp.status_code == 200
    assert trans_resp.json()["status"] == "Under_Investigation"


# ─── クローズフロー ──────────────────────────────────────────────────────────

async def test_close_problem(client, auth_headers):
    """Problem クローズフロー: New → Closed"""
    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "クローズフローテスト", "priority": "P4"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    problem_id = create_resp.json()["problem_id"]

    close_resp = await client.post(
        f"/api/v1/problems/{problem_id}/transitions",
        json={"new_status": "Closed"},
        headers=auth_headers,
    )
    assert close_resp.status_code == 200
    data = close_resp.json()
    assert data["status"] == "Closed"
    assert data["closed_at"] is not None


# ─── 一覧フィルタテスト ─────────────────────────────────────────────────────

async def test_list_problems_with_status_filter(client, auth_headers):
    """GET /problems?status=New → statusフィルタ確認"""
    await client.post(
        "/api/v1/problems",
        json={"title": "ステータスフィルタテスト", "priority": "P3"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/problems?status=New", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["status"] == "New"


async def test_list_problems_with_priority_filter(client, auth_headers):
    """GET /problems?priority=P1 → priorityフィルタ確認"""
    await client.post(
        "/api/v1/problems",
        json={"title": "優先度フィルタテスト", "priority": "P1"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/problems?priority=P1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


async def test_list_problems_with_known_error_filter(client, auth_headers):
    """GET /problems?known_error=false → known_errorフィルタ確認"""
    resp = await client.get("/api/v1/problems?known_error=false", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)


# ─── 更新 404テスト ─────────────────────────────────────────────────────────

async def test_update_problem_not_found(client, auth_headers):
    """存在しないIDの更新 → 404"""
    import uuid
    resp = await client.patch(
        f"/api/v1/problems/{uuid.uuid4()}",
        json={"root_cause": "不明"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── ステータス遷移失敗テスト ────────────────────────────────────────────────

async def test_transition_problem_invalid(client, auth_headers):
    """無効なステータス遷移 → 422"""
    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "無効遷移テスト", "priority": "P3"},
        headers=auth_headers,
    )
    problem_id = create_resp.json()["problem_id"]

    # New → Resolved は直接不可
    resp = await client.post(
        f"/api/v1/problems/{problem_id}/transitions",
        json={"new_status": "Resolved"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_transition_problem_not_found(client, auth_headers):
    """存在しないIDの遷移 → 404"""
    import uuid
    resp = await client.post(
        f"/api/v1/problems/{uuid.uuid4()}/transitions",
        json={"new_status": "Under_Investigation"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── 既知エラー404テスト ─────────────────────────────────────────────────────

async def test_known_error_not_found(client, auth_headers):
    """存在しないIDのknown-error → 404"""
    import uuid
    resp = await client.post(
        f"/api/v1/problems/{uuid.uuid4()}/known-error",
        json={"workaround": "テスト"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── フルライフサイクルテスト ────────────────────────────────────────────────

async def test_problem_full_lifecycle(client, auth_headers):
    """New → Under_Investigation → Known_Error → Resolved → Closed"""
    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "ライフサイクルテスト", "priority": "P2"},
        headers=auth_headers,
    )
    problem_id = create_resp.json()["problem_id"]

    # New → Under_Investigation
    resp = await client.post(
        f"/api/v1/problems/{problem_id}/transitions",
        json={"new_status": "Under_Investigation"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Known Error 登録
    resp = await client.post(
        f"/api/v1/problems/{problem_id}/known-error",
        json={"workaround": "定期再起動で回避"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["known_error"] is True

    # Known_Error → Resolved
    resp = await client.post(
        f"/api/v1/problems/{problem_id}/transitions",
        json={"new_status": "Resolved"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is not None

    # Resolved → Closed
    resp = await client.post(
        f"/api/v1/problems/{problem_id}/transitions",
        json={"new_status": "Closed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is not None


# ─── RCA分析エンドポイントテスト ─────────────────────────────────────────────

async def test_analyze_problem_rca(client, auth_headers):
    """POST /problems/{id}/analyze → 200, RCA結果を返す"""
    from src.services.rca_service import RCAResult

    create_resp = await client.post(
        "/api/v1/problems",
        json={"title": "RCA分析テスト", "priority": "P2"},
        headers=auth_headers,
    )
    problem_id = create_resp.json()["problem_id"]

    mock_result = RCAResult(
        problem_id=problem_id,
        candidates=[],
        similar_incidents=[],
        affected_cis=[],
        analysis_summary="テスト分析結果",
    )

    with patch(
        "src.api.v1.problems.rca_service.analyze_problem",
        new=AsyncMock(return_value=mock_result),
    ):
        resp = await client.post(
            f"/api/v1/problems/{problem_id}/analyze",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "problem_id" in data
    assert "candidates" in data
    assert "analysis_summary" in data


# ─── 認証テスト ──────────────────────────────────────────────────────────────

async def test_unauthorized_problems(client):
    """認証ヘッダーなし → 401"""
    resp = await client.get("/api/v1/problems")
    assert resp.status_code == 401


async def test_create_problem_missing_title(client, auth_headers):
    """タイトルなし → 422"""
    resp = await client.post(
        "/api/v1/problems",
        json={"priority": "P2"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
