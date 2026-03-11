"""SSO サービス - Issue #76 SSO/SAML認証統合

SAML 2.0 / OIDC フローのコアロジック:
- プロバイダー設定管理
- JIT（Just-in-Time）ユーザープロビジョニング
- グループ→ロールマッピング
- JWT トークン変換
"""

import json
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token
from src.models.sso_provider import SSOProvider
from src.models.user import User, UserRole


@dataclass
class SSOUserInfo:
    """IdP から取得したユーザー情報を正規化したデータクラス。"""

    email: str
    display_name: str
    groups: list[str]
    idp_subject: str  # IdP 側のユーザー識別子


class SSOService:
    """SSO 認証サービス。

    SAML / OIDC プロバイダーとの統合・JIT プロビジョニング・JWT 変換を担当する。
    """

    # ロール文字列 → UserRole マッピング
    ROLE_MAP: dict[str, UserRole] = {
        "system_admin": UserRole.SYSTEM_ADMIN,
        "admin": UserRole.SYSTEM_ADMIN,
        "service_manager": UserRole.SERVICE_MANAGER,
        "change_manager": UserRole.CHANGE_MANAGER,
        "incident_manager": UserRole.INCIDENT_MANAGER,
        "operator": UserRole.OPERATOR,
        "viewer": UserRole.VIEWER,
    }

    # ─── プロバイダー管理 ────────────────────────────────────────────────────

    async def create_provider(
        self,
        db: AsyncSession,
        *,
        name: str,
        provider_type: str,
        oidc_client_id: str | None = None,
        oidc_client_secret: str | None = None,
        oidc_discovery_url: str | None = None,
        saml_idp_metadata_url: str | None = None,
        saml_idp_entity_id: str | None = None,
        saml_idp_sso_url: str | None = None,
        saml_idp_certificate: str | None = None,
        group_role_mapping: dict[str, str] | None = None,
    ) -> SSOProvider:
        provider = SSOProvider(
            provider_id=uuid.uuid4(),
            name=name,
            provider_type=provider_type,
            oidc_client_id=oidc_client_id,
            oidc_client_secret=oidc_client_secret,
            oidc_discovery_url=oidc_discovery_url,
            saml_idp_metadata_url=saml_idp_metadata_url,
            saml_idp_entity_id=saml_idp_entity_id,
            saml_idp_sso_url=saml_idp_sso_url,
            saml_idp_certificate=saml_idp_certificate,
            group_role_mapping_json=json.dumps(group_role_mapping) if group_role_mapping else None,
        )
        db.add(provider)
        await db.flush()
        return provider

    async def get_provider(self, db: AsyncSession, provider_id: uuid.UUID) -> SSOProvider | None:
        result = await db.execute(select(SSOProvider).where(SSOProvider.provider_id == provider_id))
        return result.scalar_one_or_none()

    async def list_providers(self, db: AsyncSession) -> list[SSOProvider]:
        result = await db.execute(select(SSOProvider).order_by(SSOProvider.name))
        return list(result.scalars().all())

    async def delete_provider(self, db: AsyncSession, provider_id: uuid.UUID) -> bool:
        provider = await self.get_provider(db, provider_id)
        if provider is None:
            return False
        await db.delete(provider)
        await db.flush()
        return True

    # ─── グループ→ロールマッピング ────────────────────────────────────────────

    def resolve_role_from_groups(self, provider: SSOProvider, groups: list[str]) -> UserRole:
        """グループリストからロールを決定する。

        マッピング設定が存在する場合はそれを使用。
        複数グループがある場合は最上位ロールを採用。
        """
        if provider.group_role_mapping_json:
            mapping: dict[str, str] = json.loads(provider.group_role_mapping_json)
            matched_roles: list[UserRole] = []
            for group in groups:
                role_str = mapping.get(group)
                if role_str and role_str in self.ROLE_MAP:
                    matched_roles.append(self.ROLE_MAP[role_str])
            if matched_roles:
                # 優先度: SYSTEM_ADMIN > SERVICE_MANAGER > ... > VIEWER
                priority = [
                    UserRole.SYSTEM_ADMIN,
                    UserRole.SERVICE_MANAGER,
                    UserRole.CHANGE_MANAGER,
                    UserRole.INCIDENT_MANAGER,
                    UserRole.OPERATOR,
                    UserRole.VIEWER,
                ]
                for role in priority:
                    if role in matched_roles:
                        return role
        return UserRole.VIEWER

    # ─── JIT プロビジョニング ─────────────────────────────────────────────────

    async def provision_user(
        self, db: AsyncSession, provider: SSOProvider, user_info: SSOUserInfo
    ) -> User:
        """SSO ユーザー情報から DB ユーザーを JIT プロビジョニングする。

        既存ユーザーが存在する場合は情報を更新、存在しない場合は新規作成する。
        """
        result = await db.execute(select(User).where(User.email == user_info.email))
        user = result.scalar_one_or_none()

        resolved_role = self.resolve_role_from_groups(provider, user_info.groups)

        if user is None:
            # SSO ユーザーの username は email のローカル部を使用
            username = user_info.email.split("@")[0]
            user = User(
                email=user_info.email,
                username=username,
                full_name=user_info.display_name,
                role=resolved_role,
                is_active=True,
                # SSO ユーザーはパスワードなし（ハッシュはダミーで設定）
                hashed_password="sso-managed",  # noqa: S106
            )
            db.add(user)
        else:
            # 既存ユーザーの表示名とロールを更新
            user.full_name = user_info.display_name
            user.role = resolved_role

        await db.flush()
        return user

    # ─── JWT 変換 ─────────────────────────────────────────────────────────────

    def generate_token(self, user: User) -> str:
        """ServiceMatrix 内部 JWT アクセストークンを生成する。"""
        return create_access_token(data={"sub": str(user.user_id), "role": user.role})

    # ─── OIDC フロー ──────────────────────────────────────────────────────────

    def build_oidc_authorization_url(
        self, provider: SSOProvider, redirect_uri: str, state: str
    ) -> str:
        """OIDC 認可エンドポイント URL を組み立てる。

        実際の IdP URL 解決は discovery_url から行うが、ここでは設定から直接生成する。
        """
        if not provider.oidc_discovery_url or not provider.oidc_client_id:
            raise ValueError("OIDC プロバイダーの設定が不完全です")

        # discovery_url の末尾を除いてベースURLを取得
        base = provider.oidc_discovery_url.removesuffix("/.well-known/openid-configuration").rstrip(
            "/"
        )
        auth_url = f"{base}/oauth2/v1/authorize"

        params = (
            f"?client_id={provider.oidc_client_id}"
            f"&response_type=code"
            f"&scope=openid+profile+email+groups"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )
        return auth_url + params

    # ─── SAML SP メタデータ ──────────────────────────────────────────────────

    def generate_sp_metadata(self, provider: SSOProvider, sp_entity_id: str, acs_url: str) -> str:
        """SAML SP (Service Provider) メタデータ XML を生成する。

        IdP に登録するためのメタデータを返す。
        """
        return f"""<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
                  entityID="{sp_entity_id}">
  <SPSSODescriptor AuthnRequestsSigned="false"
                   WantAssertionsSigned="true"
                   protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                              Location="{acs_url}"
                              index="1"/>
  </SPSSODescriptor>
</EntityDescriptor>"""


sso_service = SSOService()
