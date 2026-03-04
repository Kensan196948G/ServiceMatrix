"""ServiceMatrix FastAPI アプリケーション"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.core.metrics import api_request_duration_seconds
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

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        if request.url.path != "/metrics":
            api_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=str(response.status_code),
            ).observe(duration)

        return response

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
