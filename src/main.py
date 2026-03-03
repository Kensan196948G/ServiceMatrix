"""ServiceMatrix FastAPI アプリケーション"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.middleware.audit import AuditMiddleware
from src.services.sla_monitor_service import sla_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await sla_monitor.start()
    yield
    await sla_monitor.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="GitHubネイティブ × AI統治型 ITサービス統治基盤",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
        contact={"name": "ServiceMatrix Team", "email": "ops@servicematrix.local"},
        license_info={"name": "MIT"},
        openapi_tags=[
            {"name": "auth", "description": "認証・認可 (JWT / RBAC)"},
            {"name": "incidents", "description": "インシデント管理 (ITIL準拠・SLA自動計算)"},
            {"name": "changes", "description": "変更管理 (CAB承認フロー・リスクスコア算出)"},
            {"name": "problems", "description": "問題管理 (Root Cause Analysis・Known Error DB)"},
            {"name": "service-requests", "description": "サービスリクエスト管理"},
            {"name": "cmdb", "description": "構成管理データベース (CI・関係・影響分析)"},
            {"name": "sla", "description": "SLA監視・違反管理"},
            {"name": "webhooks", "description": "GitHub Webhook受信 (Issues/PR連携)"},
            {"name": "health", "description": "ヘルスチェック"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
