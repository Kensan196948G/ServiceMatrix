"""SSO 認証 API - Issue #76 SSO/SAML認証統合

エンドポイント:
  POST /auth/sso/providers          - プロバイダー登録 (SystemAdmin)
  GET  /auth/sso/providers          - プロバイダー一覧 (SystemAdmin)
  GET  /auth/sso/providers/{id}     - プロバイダー取得 (SystemAdmin)
  DELETE /auth/sso/providers/{id}   - プロバイダー削除 (SystemAdmin)
  GET  /auth/sso/{id}/oidc/login    - OIDC 認可リダイレクト URL 取得
  GET  /auth/sso/{id}/saml/metadata - SAML SP メタデータ XML 取得
  POST /auth/sso/{id}/oidc/callback - OIDC コールバック (テスト用 JIT プロビジョニング)
"""

import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import require_role
from src.models.user import User, UserRole
from src.services.sso_service import SSOUserInfo, sso_service

router = APIRouter(prefix="/auth/sso", tags=["auth"])


# ─── リクエスト / レスポンスモデル ────────────────────────────────────────────


class SSOProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider_type: str = Field(pattern=r"^(saml|oidc)$")
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_discovery_url: str | None = None
    saml_idp_metadata_url: str | None = None
    saml_idp_entity_id: str | None = None
    saml_idp_sso_url: str | None = None
    saml_idp_certificate: str | None = None
    group_role_mapping: dict[str, str] | None = None


class SSOProviderResponse(BaseModel):
    provider_id: uuid.UUID
    name: str
    provider_type: str
    is_enabled: bool
    oidc_client_id: str | None
    oidc_discovery_url: str | None
    saml_idp_metadata_url: str | None
    saml_idp_entity_id: str | None
    saml_idp_sso_url: str | None

    model_config = {"from_attributes": True}


class OIDCCallbackPayload(BaseModel):
    """OIDC コールバックで受け取るユーザー情報（テスト用）。

    本番環境では IdP からの id_token を検証してこの情報を取得するが、
    ここではテスト・統合用途のためにクライアントから直接受け取る。
    """

    email: str
    display_name: str
    groups: list[str] = Field(default_factory=list)
    idp_subject: str


class SSOTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user_email: str
    role: str


# ─── プロバイダー管理エンドポイント ──────────────────────────────────────────


@router.post(
    "/providers",
    response_model=SSOProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sso_provider(
    payload: SSOProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> SSOProviderResponse:
    """SSO プロバイダーを登録する（SystemAdmin 専用）。"""
    provider = await sso_service.create_provider(
        db,
        name=payload.name,
        provider_type=payload.provider_type,
        oidc_client_id=payload.oidc_client_id,
        oidc_client_secret=payload.oidc_client_secret,
        oidc_discovery_url=payload.oidc_discovery_url,
        saml_idp_metadata_url=payload.saml_idp_metadata_url,
        saml_idp_entity_id=payload.saml_idp_entity_id,
        saml_idp_sso_url=payload.saml_idp_sso_url,
        saml_idp_certificate=payload.saml_idp_certificate,
        group_role_mapping=payload.group_role_mapping,
    )
    await db.commit()
    await db.refresh(provider)
    return SSOProviderResponse.model_validate(provider)


@router.get("/providers", response_model=list[SSOProviderResponse])
async def list_sso_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> list[SSOProviderResponse]:
    """SSO プロバイダー一覧を取得する（SystemAdmin 専用）。"""
    providers = await sso_service.list_providers(db)
    return [SSOProviderResponse.model_validate(p) for p in providers]


@router.get("/providers/{provider_id}", response_model=SSOProviderResponse)
async def get_sso_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> SSOProviderResponse:
    """SSO プロバイダーを取得する（SystemAdmin 専用）。"""
    provider = await sso_service.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO provider not found")
    return SSOProviderResponse.model_validate(provider)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sso_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> None:
    """SSO プロバイダーを削除する（SystemAdmin 専用）。"""
    deleted = await sso_service.delete_provider(db, provider_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO provider not found")
    await db.commit()


# ─── OIDC フロー ──────────────────────────────────────────────────────────────


@router.get("/{provider_id}/oidc/login")
async def oidc_login(
    provider_id: uuid.UUID,
    redirect_uri: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """OIDC 認可 URL を返す。

    クライアントはこの URL にリダイレクトして IdP の認証画面に進む。
    """
    provider = await sso_service.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO provider not found")
    if provider.provider_type != "oidc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Provider is not OIDC type"
        )

    state = secrets.token_urlsafe(32)
    auth_url = sso_service.build_oidc_authorization_url(provider, redirect_uri, state)
    return {"authorization_url": auth_url, "state": state}


@router.post("/{provider_id}/oidc/callback", response_model=SSOTokenResponse)
async def oidc_callback(
    provider_id: uuid.UUID,
    payload: OIDCCallbackPayload,
    db: AsyncSession = Depends(get_db),
) -> SSOTokenResponse:
    """OIDC コールバック処理 - JIT プロビジョニング後に JWT を発行する。

    本番では IdP から受け取った code を id_token に交換して検証する。
    このエンドポイントはテスト・開発環境向けに直接ユーザー情報を受け取る。
    """
    provider = await sso_service.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO provider not found")
    if not provider.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="SSO provider is disabled"
        )

    user_info = SSOUserInfo(
        email=payload.email,
        display_name=payload.display_name,
        groups=payload.groups,
        idp_subject=payload.idp_subject,
    )
    user = await sso_service.provision_user(db, provider, user_info)
    await db.commit()
    await db.refresh(user)

    token = sso_service.generate_token(user)
    return SSOTokenResponse(
        access_token=token,
        user_email=user.email,
        role=user.role,
    )


# ─── SAML SP メタデータ ──────────────────────────────────────────────────────


@router.get("/{provider_id}/saml/metadata", response_class=PlainTextResponse)
async def saml_sp_metadata(
    provider_id: uuid.UUID,
    sp_entity_id: str = "https://servicematrix.local/saml",
    acs_url: str = "https://servicematrix.local/api/v1/auth/sso/saml/acs",
    db: AsyncSession = Depends(get_db),
) -> str:
    """SAML SP メタデータ XML を返す。

    IdP（Okta / Azure AD 等）にサービスプロバイダーとして登録するためのメタデータ。
    """
    provider = await sso_service.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO provider not found")
    if provider.provider_type != "saml":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Provider is not SAML type"
        )

    metadata = sso_service.generate_sp_metadata(provider, sp_entity_id, acs_url)
    return PlainTextResponse(content=metadata, media_type="application/xml")
