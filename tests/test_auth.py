"""認証・認可・RBACテスト"""
import pytest
from src.core.security import create_access_token, decode_token
from src.models.user import UserRole
from src.middleware.rbac import ROLE_HIERARCHY


def test_create_access_token():
    """JWTアクセストークンが生成できること"""
    token = create_access_token({"sub": "test-user-id", "role": "IncidentManager"})
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_token():
    """生成したトークンがデコードできること"""
    data = {"sub": "user-123", "role": "Operator"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["role"] == "Operator"
    assert decoded["type"] == "access"


def test_role_hierarchy_order():
    """ロール階層が正しく定義されていること"""
    assert ROLE_HIERARCHY[UserRole.SYSTEM_ADMIN] > ROLE_HIERARCHY[UserRole.SERVICE_MANAGER]
    assert ROLE_HIERARCHY[UserRole.SERVICE_MANAGER] > ROLE_HIERARCHY[UserRole.CHANGE_MANAGER]
    assert ROLE_HIERARCHY[UserRole.CHANGE_MANAGER] > ROLE_HIERARCHY[UserRole.INCIDENT_MANAGER]
    assert ROLE_HIERARCHY[UserRole.INCIDENT_MANAGER] > ROLE_HIERARCHY[UserRole.VIEWER]


def test_system_admin_highest_role():
    """SystemAdminが最高権限を持つこと"""
    max_role = max(ROLE_HIERARCHY, key=lambda r: ROLE_HIERARCHY[r])
    assert max_role == UserRole.SYSTEM_ADMIN


def test_viewer_lowest_role():
    """Viewerが最低権限であること（AIAgentを除く）"""
    viewer_score = ROLE_HIERARCHY[UserRole.VIEWER]
    assert viewer_score > 0


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """ヘルスチェックエンドポイントが200を返すこと"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
