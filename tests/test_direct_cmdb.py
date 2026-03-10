"""CMDB API 直接呼び出しカバレッジテスト

直接呼び出しパターン（AsyncMock + await）を使用して
ASGI TestClient では追跡できない async 関数ボディをカバーする。

対象: src/api/v1/cmdb.py
カバー対象行: 40, 50, 60-62, 73-75, 99-101, 111-113, 129-166, 183-221
"""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─── テストヘルパー ─────────────────────────────────────────────────────────────

def _make_ci(**overrides):
    """CIResponse モックオブジェクトを生成"""
    now = datetime.now(timezone.utc)
    ci = MagicMock()
    ci.ci_id = overrides.get("ci_id", uuid.uuid4())
    ci.ci_name = overrides.get("ci_name", "テストサーバー")
    ci.ci_type = overrides.get("ci_type", "Server")
    ci.ci_class = overrides.get("ci_class", None)
    ci.status = overrides.get("status", "Active")
    ci.version = overrides.get("version", "1.0.0")
    ci.owner_id = overrides.get("owner_id", None)
    ci.description = overrides.get("description", "テスト用CI")
    ci.attributes = overrides.get("attributes", None)
    ci.created_at = now
    ci.updated_at = now
    return ci


def _make_relationship(**overrides):
    """CIRelationshipResponse モックオブジェクトを生成"""
    now = datetime.now(timezone.utc)
    rel = MagicMock()
    rel.relationship_id = overrides.get("relationship_id", uuid.uuid4())
    rel.source_ci_id = overrides.get("source_ci_id", uuid.uuid4())
    rel.target_ci_id = overrides.get("target_ci_id", uuid.uuid4())
    rel.relationship_type = overrides.get("relationship_type", "depends_on")
    rel.description = overrides.get("description", None)
    rel.created_at = datetime.now(timezone.utc)
    rel.updated_at = datetime.now(timezone.utc)
    return rel


def _make_impact_response(ci_id: uuid.UUID, **overrides):
    """ImpactAnalysisResponse モックオブジェクトを生成"""
    resp = MagicMock()
    resp.ci_id = ci_id
    resp.ci_name = overrides.get("ci_name", "テストCI")
    resp.direct_dependents = overrides.get("direct_dependents", [])
    resp.transitive_count = overrides.get("transitive_count", 0)
    return resp


# ─── list_cis 直接呼び出し ──────────────────────────────────────────────────

async def test_list_cis_direct_empty(db_session):
    """list_cis: CIなし → 空リスト返却"""
    from src.api.v1.cmdb import list_cis

    mock_user = MagicMock()

    with patch("src.api.v1.cmdb.cmdb_service.get_cis", new=AsyncMock(return_value=([], 0))):
        result = await list_cis(db=db_session, current_user=mock_user)
    assert result == []


async def test_list_cis_direct_with_data(db_session):
    """list_cis: CI存在 → リスト返却、フィルター引数適用"""
    from src.api.v1.cmdb import list_cis

    mock_user = MagicMock()
    ci = _make_ci()

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_cis",
        new=AsyncMock(return_value=([ci], 1)),
    ):
        result = await list_cis(
            db=db_session,
            current_user=mock_user,
            ci_type="Server",
            status_filter="Active",
            skip=0,
            limit=20,
            department="IT部門",
        )
    assert len(result) == 1
    assert result[0].ci_name == "テストサーバー"


# ─── create_ci 直接呼び出し ─────────────────────────────────────────────────

async def test_create_ci_direct_success(db_session):
    """create_ci: 正常作成 → CIオブジェクト返却"""
    from src.api.v1.cmdb import create_ci
    from src.schemas.cmdb import CICreate

    mock_user = MagicMock()
    new_ci = _make_ci(ci_name="新規サーバー", ci_type="Server")
    data = CICreate(ci_name="新規サーバー", ci_type="Server")

    with patch(
        "src.api.v1.cmdb.cmdb_service.create_ci",
        new=AsyncMock(return_value=new_ci),
    ):
        result = await create_ci(data=data, db=db_session, current_user=mock_user)
    assert result.ci_name == "新規サーバー"


# ─── get_ci 直接呼び出し ────────────────────────────────────────────────────

async def test_get_ci_direct_success(db_session):
    """get_ci: CI存在 → CIオブジェクト返却"""
    from src.api.v1.cmdb import get_ci

    mock_user = MagicMock()
    ci_id = uuid.uuid4()
    ci = _make_ci(ci_id=ci_id)

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_ci",
        new=AsyncMock(return_value=ci),
    ):
        result = await get_ci(ci_id=ci_id, db=db_session, current_user=mock_user)
    assert result.ci_id == ci_id


async def test_get_ci_direct_not_found(db_session):
    """get_ci: CI不存在 → 404 HTTPException"""
    from fastapi import HTTPException
    from src.api.v1.cmdb import get_ci

    mock_user = MagicMock()

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_ci",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_ci(ci_id=uuid.uuid4(), db=db_session, current_user=mock_user)
    assert exc_info.value.status_code == 404
    assert "CI" in exc_info.value.detail


# ─── update_ci 直接呼び出し ─────────────────────────────────────────────────

async def test_update_ci_direct_success(db_session):
    """update_ci: CI存在 → 更新後CIオブジェクト返却"""
    from src.api.v1.cmdb import update_ci
    from src.schemas.cmdb import CIUpdate

    mock_user = MagicMock()
    ci_id = uuid.uuid4()
    updated_ci = _make_ci(ci_id=ci_id, status="Maintenance", version="2.0.0")
    data = CIUpdate(status="Maintenance", version="2.0.0")

    with patch(
        "src.api.v1.cmdb.cmdb_service.update_ci",
        new=AsyncMock(return_value=updated_ci),
    ):
        result = await update_ci(
            ci_id=ci_id, data=data, db=db_session, current_user=mock_user
        )
    assert result.status == "Maintenance"
    assert result.version == "2.0.0"


async def test_update_ci_direct_not_found(db_session):
    """update_ci: CI不存在 → 404 HTTPException"""
    from fastapi import HTTPException
    from src.api.v1.cmdb import update_ci
    from src.schemas.cmdb import CIUpdate

    mock_user = MagicMock()
    data = CIUpdate(status="Inactive")

    with patch(
        "src.api.v1.cmdb.cmdb_service.update_ci",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await update_ci(
                ci_id=uuid.uuid4(), data=data, db=db_session, current_user=mock_user
            )
    assert exc_info.value.status_code == 404


# ─── create_ci_relationship 直接呼び出し ────────────────────────────────────

async def test_create_ci_relationship_direct_success(db_session):
    """create_ci_relationship: 正常 → 関係オブジェクト返却"""
    from src.api.v1.cmdb import create_ci_relationship
    from src.schemas.cmdb import CIRelationshipCreate

    mock_user = MagicMock()
    src_id = uuid.uuid4()
    tgt_id = uuid.uuid4()
    rel = _make_relationship(source_ci_id=src_id, target_ci_id=tgt_id)
    data = CIRelationshipCreate(
        source_ci_id=src_id,
        target_ci_id=tgt_id,
        relationship_type="depends_on",
    )

    with patch(
        "src.api.v1.cmdb.cmdb_service.create_ci_relationship",
        new=AsyncMock(return_value=rel),
    ):
        result = await create_ci_relationship(
            data=data, db=db_session, current_user=mock_user
        )
    assert result.relationship_type == "depends_on"


async def test_create_ci_relationship_direct_value_error(db_session):
    """create_ci_relationship: ValueError発生 → 422 HTTPException"""
    from fastapi import HTTPException
    from src.api.v1.cmdb import create_ci_relationship
    from src.schemas.cmdb import CIRelationshipCreate

    mock_user = MagicMock()
    src_id = uuid.uuid4()
    data = CIRelationshipCreate(
        source_ci_id=src_id,
        target_ci_id=src_id,  # 自己参照（ValueError想定）
        relationship_type="depends_on",
    )

    with patch(
        "src.api.v1.cmdb.cmdb_service.create_ci_relationship",
        new=AsyncMock(side_effect=ValueError("自己参照は不可")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_ci_relationship(
                data=data, db=db_session, current_user=mock_user
            )
    assert exc_info.value.status_code == 422
    assert "自己参照" in exc_info.value.detail


# ─── analyze_impact 直接呼び出し ────────────────────────────────────────────

async def test_analyze_impact_direct_success(db_session):
    """analyze_impact: CI存在 → インパクト分析結果返却"""
    from src.api.v1.cmdb import analyze_impact

    mock_user = MagicMock()
    ci_id = uuid.uuid4()
    ci = _make_ci(ci_id=ci_id)
    impact = _make_impact_response(ci_id=ci_id, transitive_count=3)

    with patch("src.api.v1.cmdb.cmdb_service.get_ci", new=AsyncMock(return_value=ci)):
        with patch(
            "src.api.v1.cmdb.cmdb_service.analyze_impact",
            new=AsyncMock(return_value=impact),
        ):
            result = await analyze_impact(
                ci_id=ci_id, db=db_session, current_user=mock_user
            )
    assert result.ci_id == ci_id
    assert result.transitive_count == 3


async def test_analyze_impact_direct_not_found(db_session):
    """analyze_impact: CI不存在 → 404 HTTPException"""
    from fastapi import HTTPException
    from src.api.v1.cmdb import analyze_impact

    mock_user = MagicMock()

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_ci", new=AsyncMock(return_value=None)
    ):
        with pytest.raises(HTTPException) as exc_info:
            await analyze_impact(
                ci_id=uuid.uuid4(), db=db_session, current_user=mock_user
            )
    assert exc_info.value.status_code == 404


# ─── export_cis 直接呼び出し ────────────────────────────────────────────────

async def test_export_cis_json(db_session):
    """export_cis: JSON形式 → JSONレスポンス返却"""
    from src.api.v1.cmdb import export_cis

    mock_user = MagicMock()
    ci_id = uuid.uuid4()
    ci = _make_ci(ci_id=ci_id, ci_name="エクスポートCI", ci_type="Server")

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_cis",
        new=AsyncMock(return_value=([ci], 1)),
    ):
        result = await export_cis(db=db_session, current_user=mock_user, format="json")

    assert result.media_type == "application/json"
    assert b"cmdb_export.json" in result.headers["Content-Disposition"].encode()
    body = json.loads(result.body)
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["ci_name"] == "エクスポートCI"


async def test_export_cis_csv(db_session):
    """export_cis: CSV形式 → CSVレスポンス返却"""
    from src.api.v1.cmdb import export_cis

    mock_user = MagicMock()
    ci = _make_ci(ci_name="CSVエクスポートCI", ci_type="Database")

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_cis",
        new=AsyncMock(return_value=([ci], 1)),
    ):
        result = await export_cis(db=db_session, current_user=mock_user, format="csv")

    assert result.media_type == "text/csv"
    assert b"cmdb_export.csv" in result.headers["Content-Disposition"].encode()
    # CSVヘッダーとデータ行を確認
    text = result.body.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["ci_name"] == "CSVエクスポートCI"
    assert rows[0]["ci_type"] == "Database"


async def test_export_cis_empty(db_session):
    """export_cis: CI無し → 空のJSONリスト"""
    from src.api.v1.cmdb import export_cis

    mock_user = MagicMock()

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_cis",
        new=AsyncMock(return_value=([], 0)),
    ):
        result = await export_cis(db=db_session, current_user=mock_user, format="json")

    body = json.loads(result.body)
    assert body == []


# ─── import_cis 直接呼び出し ────────────────────────────────────────────────

async def _make_upload_file(content: bytes, filename: str):
    """UploadFile モックを生成"""
    upload = MagicMock()
    upload.filename = filename
    upload.read = AsyncMock(return_value=content)
    return upload


async def test_import_cis_json_success(db_session):
    """import_cis: JSONファイル → 正常インポート"""
    from src.api.v1.cmdb import import_cis

    mock_user = MagicMock()
    ci_data = [
        {"ci_name": "インポートサーバー1", "ci_type": "Server"},
        {"ci_name": "インポートサーバー2", "ci_type": "Application"},
    ]
    content = json.dumps(ci_data, ensure_ascii=False).encode("utf-8")
    upload = await _make_upload_file(content, "import.json")

    with patch(
        "src.api.v1.cmdb.cmdb_service.create_ci",
        new=AsyncMock(return_value=_make_ci()),
    ):
        result = await import_cis(db=db_session, current_user=mock_user, file=upload)

    assert result.created == 2
    assert result.failed == 0
    assert result.errors == []


async def test_import_cis_csv_success(db_session):
    """import_cis: CSVファイル → 正常インポート"""
    from src.api.v1.cmdb import import_cis

    mock_user = MagicMock()
    csv_content = "ci_name,ci_type,status\nCSVサーバー,Server,Active\n"
    content = csv_content.encode("utf-8")
    upload = await _make_upload_file(content, "import.csv")

    with patch(
        "src.api.v1.cmdb.cmdb_service.create_ci",
        new=AsyncMock(return_value=_make_ci()),
    ):
        result = await import_cis(db=db_session, current_user=mock_user, file=upload)

    assert result.created == 1
    assert result.failed == 0


async def test_import_cis_empty_name_failure(db_session):
    """import_cis: CI名が空 → failed カウント増加"""
    from src.api.v1.cmdb import import_cis

    mock_user = MagicMock()
    ci_data = [{"ci_name": "", "ci_type": "Server"}]
    content = json.dumps(ci_data).encode("utf-8")
    upload = await _make_upload_file(content, "import.json")

    with patch("src.api.v1.cmdb.cmdb_service.create_ci", new=AsyncMock()):
        result = await import_cis(db=db_session, current_user=mock_user, file=upload)

    assert result.failed == 1
    assert result.created == 0
    assert len(result.errors) == 1


async def test_import_cis_partial_failure(db_session):
    """import_cis: 一部失敗 → created/failed カウント正確"""
    from src.api.v1.cmdb import import_cis

    mock_user = MagicMock()
    ci_data = [
        {"ci_name": "成功CI", "ci_type": "Server"},
        {"ci_name": "失敗CI", "ci_type": "Server"},
    ]
    content = json.dumps(ci_data).encode("utf-8")
    upload = await _make_upload_file(content, "import.json")

    # 2回目の呼び出しで例外
    create_mock = AsyncMock(
        side_effect=[_make_ci(), Exception("DB エラー")]
    )
    with patch("src.api.v1.cmdb.cmdb_service.create_ci", new=create_mock):
        result = await import_cis(db=db_session, current_user=mock_user, file=upload)

    assert result.created == 1
    assert result.failed == 1
    assert len(result.errors) == 1


async def test_import_cis_invalid_file(db_session):
    """import_cis: 不正ファイル → errors に解析エラー追加"""
    from src.api.v1.cmdb import import_cis

    mock_user = MagicMock()
    content = b"not valid json{"
    upload = await _make_upload_file(content, "import.json")

    result = await import_cis(db=db_session, current_user=mock_user, file=upload)

    # 解析エラーが errors に記録される
    assert len(result.errors) >= 1
    assert "ファイル解析エラー" in result.errors[0]


async def test_import_cis_json_with_optional_fields(db_session):
    """import_cis: オプションフィールド（ci_class, version）付きJSONインポート"""
    from src.api.v1.cmdb import import_cis

    mock_user = MagicMock()
    ci_data = [
        {
            "ci_name": "オプションCI",
            "ci_type": "Server",
            "ci_class": "Physical",
            "version": "2.1.0",
            "description": "テスト用",
        }
    ]
    content = json.dumps(ci_data, ensure_ascii=False).encode("utf-8")
    upload = await _make_upload_file(content, "import.json")

    created_ci = _make_ci(ci_class="Physical", version="2.1.0")
    with patch(
        "src.api.v1.cmdb.cmdb_service.create_ci",
        new=AsyncMock(return_value=created_ci),
    ):
        result = await import_cis(db=db_session, current_user=mock_user, file=upload)

    assert result.created == 1
    assert result.failed == 0


# ─── get_ci_relationships 直接呼び出し ─────────────────────────────────────

async def test_get_ci_relationships_direct(db_session):
    """get_ci_relationships: CI存在 → 関係リスト返却"""
    from src.api.v1.cmdb import get_ci_relationships

    mock_user = MagicMock()
    ci_id = uuid.uuid4()
    rel = _make_relationship(source_ci_id=ci_id)

    with patch(
        "src.api.v1.cmdb.cmdb_service.get_ci_relationships",
        new=AsyncMock(return_value=[rel]),
    ):
        result = await get_ci_relationships(
            ci_id=ci_id, db=db_session, current_user=mock_user
        )

    assert len(result) == 1
    assert result[0].source_ci_id == ci_id
