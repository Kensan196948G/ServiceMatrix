"""OpenTelemetry トレーシング状態確認 API - Issue #74"""

from typing import Any

from fastapi import APIRouter, Depends

from src.core.telemetry import get_current_span_id, get_current_trace_id
from src.middleware.rbac import get_current_user
from src.models.user import User

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/status", response_model=dict[str, Any])
async def get_telemetry_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """現在のトレーシング状態を返す。

    レスポンス例:
    ```json
    {
        "tracing_enabled": true,
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b7",
        "service": "servicematrix"
    }
    ```
    """
    trace_id = get_current_trace_id()
    span_id = get_current_span_id()
    return {
        "tracing_enabled": trace_id is not None,
        "trace_id": trace_id,
        "span_id": span_id,
        "service": "servicematrix",
    }
