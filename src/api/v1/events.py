"""イベントバス管理 API エンドポイント"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.event_bus import (
    STREAM_DLQ,
    STREAM_INCIDENTS,
    event_bus,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


# ── スキーマ ──────────────────────────────────────────────────────────────────


class EventPublishRequest(BaseModel):
    stream: str = Field(..., description="発行先ストリーム名")
    event_type: str = Field(..., description="イベント型 (例: incident.created)")
    payload: dict[str, Any] = Field(default_factory=dict, description="イベントペイロード")


class EventPublishResponse(BaseModel):
    message_id: str
    stream: str
    event_type: str


class StreamStatsResponse(BaseModel):
    stream: str
    length: int
    groups: int | None = None
    error: str | None = None


# ── エンドポイント ────────────────────────────────────────────────────────────


@router.get("/streams", response_model=list[dict[str, Any]])
async def list_streams():
    """登録済みストリームの統計情報一覧を返す"""
    try:
        return await event_bus.list_streams()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis接続エラー: {exc}") from exc


@router.get("/streams/{stream_name}/stats", response_model=dict[str, Any])
async def get_stream_stats(stream_name: str):
    """指定ストリームの統計情報を返す"""
    allowed = {
        "incidents": STREAM_INCIDENTS,
        "dlq": STREAM_DLQ,
        "changes": "sm:events:changes",
        "sla": "sm:events:sla",
        "notifications": "sm:events:notifications",
    }
    if stream_name not in allowed:
        raise HTTPException(
            status_code=404,
            detail=f"ストリーム '{stream_name}' は存在しません。利用可能: {list(allowed)}",
        )
    try:
        return await event_bus.get_stream_info(allowed[stream_name])
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis接続エラー: {exc}") from exc


@router.post("/publish", response_model=EventPublishResponse)
async def publish_event(req: EventPublishRequest):
    """イベントをストリームに発行する（テスト・管理用）"""
    try:
        message_id = await event_bus.publish(req.stream, req.event_type, req.payload)
        return EventPublishResponse(
            message_id=message_id,
            stream=req.stream,
            event_type=req.event_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"イベント発行エラー: {exc}") from exc


@router.get("/dlq", response_model=list[dict[str, Any]])
async def get_dlq_entries(limit: int = 20):
    """デッドレターキューのエントリ一覧を取得する"""
    try:
        client = await event_bus._get_client()
        raw = await client.xrevrange(STREAM_DLQ, count=limit)
        results = []
        for message_id, fields in raw:
            results.append(
                {
                    "message_id": message_id,
                    "original_stream": fields.get("original_stream"),
                    "original_message_id": fields.get("original_message_id"),
                    "event_type": fields.get("event_type"),
                    "error": fields.get("error"),
                }
            )
        return results
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DLQ取得エラー: {exc}") from exc
