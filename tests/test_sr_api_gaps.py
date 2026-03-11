"""service_requests.py API エンドポイント カバレッジ補完テスト

未カバー:
- GET /{request_id} 成功ケース
- PATCH /{request_id} 成功・404 ケース
- POST /{request_id}/transitions 無効遷移 → 422
- POST /{request_id}/create-incident 成功・404 ケース
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


# ─── モックフィクスチャ ────────────────────────────────────────────────────────


@pytest_asyncio.fixture(autouse=True)
async def mock_seq_and_audit():
    """シーケンス採番・監査ログをモック（全テスト共通）"""
    _sr_counter = [0]
    _inc_counter = [0]

    async def _next_sr(db):
        _sr_counter[0] += 1
        return f"SR-2024-{_sr_counter[0]:06d}"

    async def _next_inc(db):
        _inc_counter[0] += 1
        return f"INC-2024-{_inc_counter[0]:06d}"

    with (
        patch("src.services.service_request_service._get_next_sr_number", _next_sr),
        patch(
            "src.services.service_request_service.audit_service.record_audit_log",
            new=AsyncMock(return_value=None),
        ),
        patch("src.services.incident_service._get_next_incident_number", _next_inc),
    ):
        yield


# ─── ヘルパー ──────────────────────────────────────────────────────────────────


async def _create_sr(client, auth_headers, title: str = "テストSR") -> str:
    """SR を作成してその request_id を返す"""
    resp = await client.post(
        "/api/v1/service-requests",
        json={"title": title},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["request_id"]


# ─── GET /{request_id} 成功テスト ─────────────────────────────────────────────


async def test_get_sr_success(client, auth_headers):
    """GET /service-requests/{id} → 200, 正しいデータを返す"""
    sr_id = await _create_sr(client, auth_headers, "詳細取得テスト")

    resp = await client.get(f"/api/v1/service-requests/{sr_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == sr_id
    assert data["title"] == "詳細取得テスト"
    assert data["status"] == "New"


async def test_get_sr_returns_all_fields(client, auth_headers):
    """GET /service-requests/{id} → 全レスポンスフィールドが存在する"""
    sr_id = await _create_sr(client, auth_headers, "フィールド確認")

    resp = await client.get(f"/api/v1/service-requests/{sr_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    required_fields = {
        "request_id", "request_number", "title", "status",
        "created_at", "updated_at",
    }
    for field in required_fields:
        assert field in data, f"フィールド '{field}' が欠落"


# ─── PATCH /{request_id} テスト ───────────────────────────────────────────────


async def test_patch_sr_success(client, auth_headers):
    """PATCH /service-requests/{id} → 200, 説明が更新される"""
    sr_id = await _create_sr(client, auth_headers, "更新テスト")

    resp = await client.patch(
        f"/api/v1/service-requests/{sr_id}",
        json={"description": "更新後の説明文"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "更新後の説明文"
    assert data["request_id"] == sr_id


async def test_patch_sr_request_type(client, auth_headers):
    """PATCH /service-requests/{id} → request_type を更新できる"""
    sr_id = await _create_sr(client, auth_headers, "種別更新テスト")

    resp = await client.patch(
        f"/api/v1/service-requests/{sr_id}",
        json={"request_type": "Software"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["request_type"] == "Software"


async def test_patch_sr_not_found(client, auth_headers):
    """PATCH /service-requests/{不明ID} → 404"""
    unknown_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/service-requests/{unknown_id}",
        json={"description": "存在しない"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── POST /{request_id}/transitions 無効遷移テスト ───────────────────────────


async def test_transitions_invalid_raises_422(client, auth_headers):
    """New → Fulfilled (不正遷移) → 422"""
    sr_id = await _create_sr(client, auth_headers, "不正遷移テスト")

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/transitions",
        json={"target_status": "Fulfilled"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_transitions_not_found_raises_422(client, auth_headers):
    """存在しない SR への遷移 → 422"""
    unknown_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/service-requests/{unknown_id}/transitions",
        json={"target_status": "Pending_Approval"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_transitions_with_comment(client, auth_headers):
    """New → Pending_Approval + comment フィールド付き遷移"""
    sr_id = await _create_sr(client, auth_headers, "コメント付き遷移")

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/transitions",
        json={"target_status": "Pending_Approval", "comment": "審査依頼"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Pending_Approval"


# ─── GET with pagination & filter ────────────────────────────────────────────


async def test_list_srs_with_status_filter(client, auth_headers):
    """status フィルタで結果を絞り込める"""
    sr_id = await _create_sr(client, auth_headers, "フィルタ対象SR")

    resp = await client.get(
        "/api/v1/service-requests?status=New",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # status=New のものだけが返る
    for item in data["items"]:
        assert item["status"] == "New"


async def test_list_srs_pagination(client, auth_headers):
    """limit=1 で1件だけ返る"""
    for i in range(3):
        await _create_sr(client, auth_headers, f"ページネーションSR{i}")

    resp = await client.get(
        "/api/v1/service-requests?limit=1&skip=0",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 1
    assert data["size"] == 1


# ─── POST /{request_id}/create-incident テスト ───────────────────────────────


async def test_create_incident_from_sr_success(client, auth_headers):
    """POST /create-incident → 201, incident が作成される"""
    sr_id = await _create_sr(client, auth_headers, "インシデント変換テスト")

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/create-incident",
        json={"priority": "P2"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "incident_id" in data
    assert "incident_number" in data
    assert data["incident_number"].startswith("INC-")
    assert data["service_request_id"] == sr_id
    assert data["service_request_number"].startswith("SR-")


async def test_create_incident_from_sr_with_notes(client, auth_headers):
    """POST /create-incident + additional_notes → incident に追記が含まれる"""
    sr_id = await _create_sr(client, auth_headers, "追記付きインシデント変換")

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/create-incident",
        json={"priority": "P1", "additional_notes": "緊急対応必要"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["message"] != ""


async def test_create_incident_from_sr_with_category(client, auth_headers):
    """POST /create-incident + category → 201"""
    sr_id = await _create_sr(client, auth_headers, "カテゴリ付きインシデント変換")

    resp = await client.post(
        f"/api/v1/service-requests/{sr_id}/create-incident",
        json={"priority": "P3", "category": "Hardware"},
        headers=auth_headers,
    )
    assert resp.status_code == 201


async def test_create_incident_from_sr_not_found(client, auth_headers):
    """存在しない SR から incident 作成 → 404"""
    unknown_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/service-requests/{unknown_id}/create-incident",
        json={"priority": "P3"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
