"""リクエストサニタイザーミドルウェア - OWASP A05/A08対応"""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

# ── 制限値 ────────────────────────────────────────────────────────────────────

# リクエストボディの最大サイズ（10MB）
MAX_BODY_SIZE_BYTES = 10 * 1024 * 1024

# 許可するContent-Typeのプレフィックス（POSTリクエスト時）
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
    "text/plain",
}

# 不審なヘッダー値のパターン
_SUSPICIOUS_HEADER_PREFIXES = ("${", "{{", "<%", "<script")


# ── ミドルウェア ──────────────────────────────────────────────────────────────


class RequestSanitizerMiddleware(BaseHTTPMiddleware):
    """リクエストの基本的なセキュリティチェックを行うミドルウェア。

    - ボディサイズ制限（10MB超でリジェクト）
    - Content-Type検証（JSON/Form以外でリジェクト）
    - 不審なヘッダー値の検出（ログ警告のみ、拒否はしない）
    """

    def __init__(
        self,
        app,
        max_body_size: int = MAX_BODY_SIZE_BYTES,
        enforce_content_type: bool = True,
    ) -> None:
        super().__init__(app)
        self._max_body_size = max_body_size
        self._enforce_content_type = enforce_content_type

    async def dispatch(self, request: Request, call_next):
        # ── 1. ボディサイズチェック ──────────────────────────────────────────
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                body_size = int(content_length)
            except ValueError:
                body_size = 0
            if body_size > self._max_body_size:
                logger.warning(
                    "request_body_too_large",
                    content_length=body_size,
                    limit=self._max_body_size,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            f"リクエストボディが大きすぎます。"
                            f"最大 {self._max_body_size // 1024 // 1024}MB です。"
                        )
                    },
                )

        # ── 2. Content-Type チェック（ボディ有りリクエストのみ） ─────────────
        if self._enforce_content_type and request.method in ("POST", "PUT", "PATCH"):
            raw_content_type = request.headers.get("content-type", "")
            media_type = raw_content_type.split(";")[0].strip().lower()
            if media_type and media_type not in ALLOWED_CONTENT_TYPES:
                logger.warning(
                    "invalid_content_type",
                    content_type=raw_content_type,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=415,
                    content={"detail": f"未対応のContent-Type: {raw_content_type}"},
                )

        # ── 3. 不審なヘッダー値の検出（ログのみ） ────────────────────────────
        for header_name, header_value in request.headers.items():
            lower_val = header_value.lower()
            if any(lower_val.startswith(prefix) for prefix in _SUSPICIOUS_HEADER_PREFIXES):
                logger.warning(
                    "suspicious_header_detected",
                    header=header_name,
                    value_prefix=header_value[:50],
                    path=request.url.path,
                )

        return await call_next(request)
