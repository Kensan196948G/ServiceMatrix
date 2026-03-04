"""ServiceCatalog エンドポイント関数の直接呼び出しユニットテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.v1.service_catalog import (
    create_service_catalog,
    delete_service_catalog,
    get_service_catalog,
    list_service_catalog,
    request_from_catalog,
    update_service_catalog,
)
from src.models.service_catalog import ServiceCatalog
from src.models.user import User, UserRole
from src.schemas.service_catalog import ServiceCatalogCreate, ServiceCatalogUpdate

pytestmark = pytest.mark.asyncio

NOW = datetime.now(timezone.utc)


def _make_catalog(**kwargs) -> MagicMock:
    defaults = {
        "catalog_id": uuid.uuid4(),
        "name": "テストサービス",
        "description": "説明",
        "category": "IT",
        "sla_hours": 8,
        "is_active": True,
        "created_at": NOW,
    }
    defaults.update(kwargs)
    cat = MagicMock(spec=ServiceCatalog)
    for k, v in defaults.items():
        setattr(cat, k, v)
    return cat


def _make_db_with(obj):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    result.scalars.return_value.all.return_value = [obj] if obj else []
    db.execute.return_value = result
    return db


def _make_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.user_id = uuid.uuid4()
    user.role = UserRole.SYSTEM_ADMIN
    return user


# ─── list_service_catalog ─────────────────────────────────────────────────────


async def test_list_service_catalog_direct():
    """list_service_catalog: DBから全件返す"""
    cat = _make_catalog()
    db = _make_db_with(cat)
    result = await list_service_catalog(db=db)
    assert len(result) == 1


# ─── get_service_catalog ──────────────────────────────────────────────────────


async def test_get_service_catalog_found_direct():
    """get_service_catalog: 見つかれば返す"""
    cat = _make_catalog()
    db = _make_db_with(cat)
    result = await get_service_catalog(catalog_id=cat.catalog_id, db=db)
    assert result == cat


async def test_get_service_catalog_not_found_direct():
    """get_service_catalog: 見つからなければ404"""
    from fastapi import HTTPException

    db = _make_db_with(None)
    with pytest.raises(HTTPException) as exc:
        await get_service_catalog(catalog_id=uuid.uuid4(), db=db)
    assert exc.value.status_code == 404


# ─── create_service_catalog ───────────────────────────────────────────────────


async def test_create_service_catalog_direct():
    """create_service_catalog: カタログ追加"""
    db = AsyncMock()
    cat = _make_catalog()
    db.refresh = AsyncMock(return_value=None)

    async def fake_refresh(obj):
        pass

    db.refresh = fake_refresh

    data = ServiceCatalogCreate(name="新サービス", category="HW", sla_hours=4)
    user = _make_user()

    # patch uuid.uuid4 inside the module to return a fixed id
    import src.api.v1.service_catalog as sc_module

    fixed_id = uuid.uuid4()
    original_uuid4 = uuid.uuid4

    # We just need to verify the function calls db.add and db.flush
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    result = await create_service_catalog(data=data, db=db, current_user=user)
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


# ─── update_service_catalog ───────────────────────────────────────────────────


async def test_update_service_catalog_direct():
    """update_service_catalog: 既存カタログを更新"""
    cat = _make_catalog()
    db = _make_db_with(cat)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    data = ServiceCatalogUpdate(name="更新後", sla_hours=16)
    user = _make_user()

    result = await update_service_catalog(
        catalog_id=cat.catalog_id, data=data, db=db, current_user=user
    )
    # setattr was called on the mock catalog
    assert cat.name == "更新後"


async def test_update_service_catalog_not_found_direct():
    """update_service_catalog: 存在しない → 404"""
    from fastapi import HTTPException

    db = _make_db_with(None)
    data = ServiceCatalogUpdate(name="X")
    user = _make_user()

    with pytest.raises(HTTPException) as exc:
        await update_service_catalog(
            catalog_id=uuid.uuid4(), data=data, db=db, current_user=user
        )
    assert exc.value.status_code == 404


# ─── delete_service_catalog ───────────────────────────────────────────────────


async def test_delete_service_catalog_direct():
    """delete_service_catalog: 削除呼び出し"""
    cat = _make_catalog()
    db = _make_db_with(cat)
    db.delete = AsyncMock()
    user = _make_user()

    await delete_service_catalog(catalog_id=cat.catalog_id, db=db, current_user=user)
    db.delete.assert_awaited_once_with(cat)


async def test_delete_service_catalog_not_found_direct():
    """delete_service_catalog: 存在しない → 404"""
    from fastapi import HTTPException

    db = _make_db_with(None)
    user = _make_user()

    with pytest.raises(HTTPException) as exc:
        await delete_service_catalog(catalog_id=uuid.uuid4(), db=db, current_user=user)
    assert exc.value.status_code == 404


# ─── request_from_catalog ─────────────────────────────────────────────────────


async def test_request_from_catalog_direct():
    """request_from_catalog: SRを生成して返す"""
    from unittest.mock import patch

    cat = _make_catalog()
    db = _make_db_with(cat)
    user = _make_user()

    mock_sr = MagicMock()
    mock_sr.request_id = uuid.uuid4()
    mock_sr.request_number = "SR-2024-000001"
    mock_sr.title = cat.name
    mock_sr.request_type = cat.category
    mock_sr.catalog_id = cat.catalog_id

    with patch(
        "src.api.v1.service_catalog.service_request_service.create_service_request",
        new=AsyncMock(return_value=mock_sr),
    ):
        result = await request_from_catalog(
            catalog_id=cat.catalog_id, db=db, current_user=user
        )
    assert result == mock_sr


async def test_request_from_catalog_not_found_direct():
    """request_from_catalog: 存在しない → 404"""
    from fastapi import HTTPException

    db = _make_db_with(None)
    user = _make_user()

    with pytest.raises(HTTPException) as exc:
        await request_from_catalog(catalog_id=uuid.uuid4(), db=db, current_user=user)
    assert exc.value.status_code == 404
