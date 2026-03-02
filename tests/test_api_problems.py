"""問題管理 API エンドポイント統合テスト"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch

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
