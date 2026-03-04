"""ServiceMatrix FastAPI アプリケーション"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.middleware.audit import AuditMiddleware
from src.middleware.metrics import MetricsMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware
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
        description="""
## ServiceMatrix - GitHubネイティブ × AI統治型 ITサービス統治基盤

ServiceMatrix は ITIL v4 準拠の IT サービス管理プラットフォームです。

### 主な機能

- 🚨 **インシデント管理** - SLA自動計算・AIトリアージ・一括担当者割り当て
- 🔄 **変更管理** - CAB承認フロー・AI変更リスクスコア算出
- 🔍 **問題管理** - Root Cause Analysis・Known Error DB
- 📋 **サービスリクエスト** - 承認ワークフロー・インシデント自動生成
- 🗄 **CMDB** - 構成アイテム管理・依存関係グラフ
- 📊 **SLA監視** - リアルタイムアラート・WebSocket通知
- 🤖 **AI機能** - トリアージ自動化・RCA推奨

### 認証

Bearer Token (JWT) 認証を使用します。
`/api/v1/auth/login` でトークンを取得後、
`Authorization: Bearer <token>` ヘッダーに設定してください。

### ページネーション

一覧APIは `page` / `size` パラメータでページネーションを制御します。
レスポンスは `PaginatedResponse` 形式: `{ items, total, page, size, pages }` です。
""",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        contact={"name": "ServiceMatrix Team", "email": "ops@servicematrix.local"},
        license_info={"name": "MIT"},
        openapi_tags=[
            {
                "name": "auth",
                "description": (
                    "JWT認証・ユーザー管理・RBAC権限制御。"
                    "ログイン・トークンリフレッシュ・ユーザーCRUDを提供します。"
                ),
            },
            {
                "name": "incidents",
                "description": (
                    "インシデント管理（ITIL準拠）。"
                    "SLA自動計算・ステータス遷移・AIトリアージ・一括担当者割り当て。"
                ),
            },
            {
                "name": "changes",
                "description": (
                    "変更管理。CAB承認フロー・AI変更リスクスコア算出・承認/却下ワークフロー。"
                ),
            },
            {
                "name": "problems",
                "description": (
                    "問題管理。Root Cause Analysis自動実行・Known Error DB・ワークアラウンド管理。"
                ),
            },
            {
                "name": "service-requests",
                "description": (
                    "サービスリクエスト管理。"
                    "承認ワークフロー・インシデント自動生成・完了/失敗記録。"
                ),
            },
            {
                "name": "cmdb",
                "description": (
                    "構成管理データベース。構成アイテム(CI)のCRUD・タグ管理・依存関係記録。"
                ),
            },
            {
                "name": "sla",
                "description": (
                    "SLA監視。違反インシデント一覧・"
                    "ダッシュボード統計・WebSocketリアルタイムアラート。"
                ),
            },
            {
                "name": "webhooks",
                "description": (
                    "GitHub Webhook受信。Issues/PRイベントからインシデット自動生成・クローズ連携。"
                ),
            },
            {
                "name": "ai",
                "description": "AI機能。インシデントトリアージ・問題RCA分析・変更リスク評価。",
            },
            {
                "name": "audit",
                "description": ("監査ログ。J-SOX対応SHA-256ハッシュチェーン・操作履歴の不変記録。"),
            },
            {
                "name": "health",
                "description": "ヘルスチェック・サービス稼働状況確認。",
            },
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
    app.add_middleware(MetricsMiddleware)
    if settings.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware, calls=settings.rate_limit_per_minute, period=60)

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
