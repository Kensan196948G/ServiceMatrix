"""入力バリデーション - OWASP Top 10 A03インジェクション防止"""

from __future__ import annotations

import re

import structlog
from fastapi import HTTPException, Query

logger = structlog.get_logger(__name__)

# ── 検出パターン ──────────────────────────────────────────────────────────────

# SQLインジェクション検出パターン（典型的な攻撃文字列）
_SQL_INJECTION_PATTERN = re.compile(
    r"(--|;|'|\"|\bOR\b|\bAND\b|\bUNION\b|\bSELECT\b|\bDROP\b|\bINSERT\b|"
    r"\bDELETE\b|\bUPDATE\b|\bEXEC\b|\bSCRIPT\b|\bXP_)",
    re.IGNORECASE,
)

# XSS検出パターン（スクリプトタグ・イベントハンドラ）
_XSS_PATTERN = re.compile(
    r"(<\s*script|javascript:|on\w+\s*=|<\s*iframe|<\s*object|<\s*embed)",
    re.IGNORECASE,
)

# パストラバーサル検出パターン
_PATH_TRAVERSAL_PATTERN = re.compile(
    r"(\.\./|\.\.\\|%2e%2e[/\\]|%252e%252e)",
    re.IGNORECASE,
)

# 最大文字列長（検索クエリ等）
MAX_QUERY_LENGTH = 500
MAX_FIELD_LENGTH = 10_000


# ── バリデーション関数 ────────────────────────────────────────────────────────


def contains_sql_injection(value: str) -> bool:
    """SQLインジェクションパターンを検出する。"""
    return bool(_SQL_INJECTION_PATTERN.search(value))


def contains_xss(value: str) -> bool:
    """XSSパターンを検出する。"""
    return bool(_XSS_PATTERN.search(value))


def contains_path_traversal(value: str) -> bool:
    """パストラバーサルパターンを検出する。"""
    return bool(_PATH_TRAVERSAL_PATTERN.search(value))


def validate_string(
    value: str,
    field_name: str = "value",
    max_length: int = MAX_FIELD_LENGTH,
    check_sql: bool = True,
    check_xss: bool = True,
    check_path: bool = False,
) -> str:
    """文字列の安全性を検証する。

    Args:
        value: 検証対象文字列
        field_name: エラーメッセージ用フィールド名
        max_length: 最大文字数
        check_sql: SQLインジェクション検査を有効化
        check_xss: XSS検査を有効化
        check_path: パストラバーサル検査を有効化

    Returns:
        検証済みの文字列

    Raises:
        HTTPException: 検証失敗時（400）
    """
    if len(value) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"'{field_name}' は {max_length} 文字以内にしてください",
        )

    if check_sql and contains_sql_injection(value):
        logger.warning("sql_injection_detected", field=field_name, value_prefix=value[:50])
        raise HTTPException(
            status_code=400,
            detail=f"'{field_name}' に不正な文字列が含まれています",
        )

    if check_xss and contains_xss(value):
        logger.warning("xss_detected", field=field_name, value_prefix=value[:50])
        raise HTTPException(
            status_code=400,
            detail=f"'{field_name}' に不正なスクリプトが含まれています",
        )

    if check_path and contains_path_traversal(value):
        logger.warning("path_traversal_detected", field=field_name, value_prefix=value[:50])
        raise HTTPException(
            status_code=400,
            detail=f"'{field_name}' に不正なパスが含まれています",
        )

    return value


# ── FastAPI Depends() バリデーター ────────────────────────────────────────────


def safe_search_query(
    q: str | None = Query(None, max_length=MAX_QUERY_LENGTH, description="検索クエリ"),
) -> str | None:
    """検索クエリパラメータのバリデーター（Depends用）。

    Usage:
        @router.get("/search")
        async def search(query: str | None = Depends(safe_search_query)):
            ...
    """
    if q is None:
        return None
    return validate_string(q, field_name="q", max_length=MAX_QUERY_LENGTH)
