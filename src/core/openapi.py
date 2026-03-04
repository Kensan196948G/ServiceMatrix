"""カスタムOpenAPIスキーマ生成"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="ServiceMatrix API",
        version="1.0.0",
        description=(
            "ServiceMatrix - GitHubネイティブ × AI統治型 ITサービス管理基盤\n\n"
            "## 認証\n"
            "Bearer JWTトークンを使用してください。"
        ),
        routes=app.routes,
    )

    # セキュリティスキーム追加
    openapi_schema.setdefault("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema
