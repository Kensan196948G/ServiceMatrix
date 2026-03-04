"""auth.py エンドポイント関数の直接呼び出しユニットテスト

ASGITransport経由ではcoverageがasync関数本体を追跡できない問題を
回避するため、エンドポイント関数を直接呼び出してカバレッジを取得する。
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.auth import login, refresh_token, get_me
from src.models.user import User, UserRole
from src.schemas.auth import LoginRequest, RefreshRequest

pytestmark = pytest.mark.asyncio


def _make_user(**overrides):
    defaults = {
        "user_id": uuid.uuid4(),
        "username": "testadmin",
        "email": "admin@test.com",
        "hashed_password": "hashedpass",
        "role": UserRole.SYSTEM_ADMIN,
        "is_active": True,
        "full_name": None,
        "last_login_at": None,
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _mock_db_with_user(user):
    """DBセッションモックを生成 - execute -> scalar_one_or_none -> user"""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    db.execute.return_value = result_mock
    return db


# ─── login() テスト ───────────────────────────────────────────────────────────


async def test_login_success_direct():
    """login() 直接呼び出し: 正常ログイン → TokenResponse"""
    user = _make_user()
    db = _mock_db_with_user(user)

    creds = LoginRequest(username="testadmin", password="testpass123")
    mock_request = MagicMock()
    mock_request.client = MagicMock()
    mock_request.client.host = "127.0.0.1"

    with (
        patch("src.api.v1.auth.verify_password", return_value=True),
        patch("src.api.v1.auth.create_access_token", return_value="access.tok"),
        patch("src.api.v1.auth.create_refresh_token", return_value="refresh.tok"),
    ):
        result = await login(request=mock_request, credentials=creds, db=db)

    assert result.access_token == "access.tok"
    assert result.refresh_token == "refresh.tok"
    assert result.token_type == "bearer"
    assert user.last_login_at is not None
    db.flush.assert_awaited_once()


async def test_login_wrong_password_direct():
    """login() 直接呼び出し: パスワード不正 → 401"""
    from fastapi import HTTPException

    user = _make_user()
    db = _mock_db_with_user(user)

    creds = LoginRequest(username="testadmin", password="wrong")
    mock_request = MagicMock()

    with (
        patch("src.api.v1.auth.verify_password", return_value=False),
        pytest.raises(HTTPException) as exc_info,
    ):
        await login(request=mock_request, credentials=creds, db=db)

    assert exc_info.value.status_code == 401


async def test_login_user_not_found_direct():
    """login() 直接呼び出し: ユーザー不在 → 401"""
    from fastapi import HTTPException

    db = _mock_db_with_user(None)
    creds = LoginRequest(username="ghost", password="any")
    mock_request = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await login(request=mock_request, credentials=creds, db=db)

    assert exc_info.value.status_code == 401


async def test_login_inactive_user_direct():
    """login() 直接呼び出し: 非アクティブユーザー → 403"""
    from fastapi import HTTPException

    user = _make_user(is_active=False)
    db = _mock_db_with_user(user)

    creds = LoginRequest(username="testadmin", password="testpass123")
    mock_request = MagicMock()

    with (
        patch("src.api.v1.auth.verify_password", return_value=True),
        pytest.raises(HTTPException) as exc_info,
    ):
        await login(request=mock_request, credentials=creds, db=db)

    assert exc_info.value.status_code == 403


# ─── refresh_token() テスト ───────────────────────────────────────────────────


async def test_refresh_token_success_direct():
    """refresh_token() 直接呼び出し: 正常リフレッシュ → TokenResponse"""
    user_id = uuid.uuid4()
    user = _make_user(user_id=user_id)
    db = _mock_db_with_user(user)

    req = RefreshRequest(refresh_token="valid.refresh.tok")

    with (
        patch(
            "src.api.v1.auth.decode_token",
            return_value={"sub": str(user_id), "type": "refresh"},
        ),
        patch("src.api.v1.auth.create_access_token", return_value="new.access"),
        patch("src.api.v1.auth.create_refresh_token", return_value="new.refresh"),
    ):
        result = await refresh_token(request=req, db=db)

    assert result.access_token == "new.access"
    assert result.refresh_token == "new.refresh"


async def test_refresh_token_not_refresh_type_direct():
    """refresh_token() 直接呼び出し: type!=refresh → 401"""
    from fastapi import HTTPException

    db = AsyncMock()
    req = RefreshRequest(refresh_token="access.tok")

    with (
        patch(
            "src.api.v1.auth.decode_token",
            return_value={"sub": "user-id", "type": "access"},
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await refresh_token(request=req, db=db)

    assert exc_info.value.status_code == 401


async def test_refresh_token_invalid_token_direct():
    """refresh_token() 直接呼び出し: decode失敗 → 401"""
    from fastapi import HTTPException

    db = AsyncMock()
    req = RefreshRequest(refresh_token="garbage")

    with (
        patch("src.api.v1.auth.decode_token", side_effect=ValueError("bad token")),
        pytest.raises(HTTPException) as exc_info,
    ):
        await refresh_token(request=req, db=db)

    assert exc_info.value.status_code == 401


async def test_refresh_token_user_inactive_direct():
    """refresh_token() 直接呼び出し: ユーザー非アクティブ → 401"""
    from fastapi import HTTPException

    user = _make_user(is_active=False)
    db = _mock_db_with_user(user)
    req = RefreshRequest(refresh_token="valid.refresh.tok")

    with (
        patch(
            "src.api.v1.auth.decode_token",
            return_value={"sub": str(user.user_id), "type": "refresh"},
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await refresh_token(request=req, db=db)

    assert exc_info.value.status_code == 401


async def test_refresh_token_user_not_found_direct():
    """refresh_token() 直接呼び出し: ユーザー不在 → 401"""
    from fastapi import HTTPException

    db = _mock_db_with_user(None)
    req = RefreshRequest(refresh_token="valid.refresh.tok")

    with (
        patch(
            "src.api.v1.auth.decode_token",
            return_value={"sub": str(uuid.uuid4()), "type": "refresh"},
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await refresh_token(request=req, db=db)

    assert exc_info.value.status_code == 401


# ─── get_me() テスト ──────────────────────────────────────────────────────────


async def test_get_me_direct():
    """get_me() 直接呼び出し: 現在ユーザーを返す"""
    user = _make_user()
    result = await get_me(current_user=user)
    assert result == user
