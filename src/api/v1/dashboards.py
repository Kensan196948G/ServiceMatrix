"""カスタムダッシュボードビルダー API"""

import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import get_db
from src.models.dashboard import Dashboard, DashboardWidget, WidgetType

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


# ── スキーマ ──────────────────────────────────────────────────────────────────


class WidgetPosition(BaseModel):
    x: int = 0
    y: int = 0
    w: int = 4
    h: int = 3


class DashboardCreate(BaseModel):
    name: str
    description: str | None = None
    tenant_id: uuid.UUID | None = None
    layout_json: str | None = None
    is_public: bool = False
    is_default: bool = False


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    layout_json: str | None = None
    is_public: bool | None = None
    is_default: bool | None = None


class WidgetCreate(BaseModel):
    widget_type: WidgetType
    title: str
    config_json: str | None = None
    position: WidgetPosition | None = None
    display_order: int = 0


class WidgetUpdate(BaseModel):
    title: str | None = None
    config_json: str | None = None
    position: WidgetPosition | None = None
    display_order: int | None = None


def _dashboard_to_dict(d: Dashboard) -> dict:
    return {
        "dashboard_id": str(d.dashboard_id),
        "name": d.name,
        "description": d.description,
        "owner_id": str(d.owner_id) if d.owner_id else None,
        "tenant_id": str(d.tenant_id) if d.tenant_id else None,
        "layout_json": d.layout_json,
        "is_public": d.is_public,
        "share_token": d.share_token,
        "is_default": d.is_default,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


def _widget_to_dict(w: DashboardWidget) -> dict:
    return {
        "widget_id": str(w.widget_id),
        "dashboard_id": str(w.dashboard_id),
        "widget_type": w.widget_type,
        "title": w.title,
        "config_json": w.config_json,
        "position_json": w.position_json,
        "display_order": w.display_order,
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
    }


# ── ダッシュボード CRUD ────────────────────────────────────────────────────────


@router.post("/", status_code=201)
async def create_dashboard(
    body: DashboardCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """ダッシュボードを作成"""
    dashboard = Dashboard(
        name=body.name,
        description=body.description,
        tenant_id=body.tenant_id,
        layout_json=body.layout_json,
        is_public=body.is_public,
        is_default=body.is_default,
    )
    session.add(dashboard)
    await session.flush()
    await session.refresh(dashboard)
    return _dashboard_to_dict(dashboard)


@router.get("/")
async def list_dashboards(
    tenant_id: uuid.UUID | None = Query(None),
    is_public: bool | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """ダッシュボード一覧"""
    stmt = select(Dashboard)
    if tenant_id is not None:
        stmt = stmt.where(Dashboard.tenant_id == tenant_id)
    if is_public is not None:
        stmt = stmt.where(Dashboard.is_public == is_public)
    result = await session.execute(stmt.order_by(Dashboard.created_at.desc()).limit(200))
    return [_dashboard_to_dict(d) for d in result.scalars().all()]


@router.get("/shared/{share_token}")
async def get_shared_dashboard(
    share_token: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """共有 URL からダッシュボードを取得（認証不要）"""
    result = await session.execute(
        select(Dashboard)
        .where(Dashboard.share_token == share_token, Dashboard.is_public.is_(True))
        .options(selectinload(Dashboard.widgets))
    )
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="ダッシュボードが見つかりません")
    data = _dashboard_to_dict(dashboard)
    data["widgets"] = [_widget_to_dict(w) for w in dashboard.widgets]
    return data


@router.get("/{dashboard_id}")
async def get_dashboard(
    dashboard_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """ダッシュボード単件取得"""
    result = await session.execute(
        select(Dashboard)
        .where(Dashboard.dashboard_id == dashboard_id)
        .options(selectinload(Dashboard.widgets))
    )
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="ダッシュボードが見つかりません")
    data = _dashboard_to_dict(dashboard)
    data["widgets"] = [_widget_to_dict(w) for w in dashboard.widgets]
    return data


@router.patch("/{dashboard_id}")
async def update_dashboard(
    dashboard_id: uuid.UUID,
    body: DashboardUpdate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """ダッシュボード更新"""
    result = await session.execute(
        select(Dashboard).where(Dashboard.dashboard_id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="ダッシュボードが見つかりません")
    if body.name is not None:
        dashboard.name = body.name
    if body.description is not None:
        dashboard.description = body.description
    if body.layout_json is not None:
        dashboard.layout_json = body.layout_json
    if body.is_public is not None:
        dashboard.is_public = body.is_public
    if body.is_default is not None:
        dashboard.is_default = body.is_default
    await session.flush()
    await session.refresh(dashboard)
    return _dashboard_to_dict(dashboard)


@router.post("/{dashboard_id}/share")
async def generate_share_token(
    dashboard_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """共有トークンを生成（is_public=True に設定）"""
    result = await session.execute(
        select(Dashboard).where(Dashboard.dashboard_id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="ダッシュボードが見つかりません")
    dashboard.share_token = secrets.token_urlsafe(32)
    dashboard.is_public = True
    await session.flush()
    await session.refresh(dashboard)
    return {
        "dashboard_id": str(dashboard.dashboard_id),
        "share_token": dashboard.share_token,
        "share_url": f"/api/v1/dashboards/shared/{dashboard.share_token}",
    }


@router.delete("/{dashboard_id}", status_code=204)
async def delete_dashboard(
    dashboard_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """ダッシュボード削除"""
    result = await session.execute(
        select(Dashboard).where(Dashboard.dashboard_id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="ダッシュボードが見つかりません")
    await session.delete(dashboard)
    await session.flush()


# ── ウィジェット CRUD ──────────────────────────────────────────────────────────


@router.post("/{dashboard_id}/widgets", status_code=201)
async def add_widget(
    dashboard_id: uuid.UUID,
    body: WidgetCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """ウィジェットを追加"""
    result = await session.execute(
        select(Dashboard).where(Dashboard.dashboard_id == dashboard_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="ダッシュボードが見つかりません")

    position_json = None
    if body.position:
        position_json = json.dumps(body.position.model_dump())

    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        widget_type=body.widget_type,
        title=body.title,
        config_json=body.config_json,
        position_json=position_json,
        display_order=body.display_order,
    )
    session.add(widget)
    await session.flush()
    await session.refresh(widget)
    return _widget_to_dict(widget)


@router.get("/{dashboard_id}/widgets")
async def list_widgets(
    dashboard_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """ウィジェット一覧"""
    result = await session.execute(
        select(DashboardWidget)
        .where(DashboardWidget.dashboard_id == dashboard_id)
        .order_by(DashboardWidget.display_order)
    )
    return [_widget_to_dict(w) for w in result.scalars().all()]


@router.patch("/{dashboard_id}/widgets/{widget_id}")
async def update_widget(
    dashboard_id: uuid.UUID,
    widget_id: uuid.UUID,
    body: WidgetUpdate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """ウィジェット更新（タイトル・設定・位置）"""
    result = await session.execute(
        select(DashboardWidget).where(
            DashboardWidget.widget_id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
    )
    widget = result.scalar_one_or_none()
    if widget is None:
        raise HTTPException(status_code=404, detail="ウィジェットが見つかりません")
    if body.title is not None:
        widget.title = body.title
    if body.config_json is not None:
        widget.config_json = body.config_json
    if body.position is not None:
        widget.position_json = json.dumps(body.position.model_dump())
    if body.display_order is not None:
        widget.display_order = body.display_order
    await session.flush()
    await session.refresh(widget)
    return _widget_to_dict(widget)


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def delete_widget(
    dashboard_id: uuid.UUID,
    widget_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """ウィジェット削除"""
    result = await session.execute(
        select(DashboardWidget).where(
            DashboardWidget.widget_id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
    )
    widget = result.scalar_one_or_none()
    if widget is None:
        raise HTTPException(status_code=404, detail="ウィジェットが見つかりません")
    await session.delete(widget)
    await session.flush()


@router.get("/{dashboard_id}/widgets/{widget_id}/data")
async def get_widget_data(
    dashboard_id: uuid.UUID,
    widget_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """ウィジェットのリアルタイムデータを取得"""
    result = await session.execute(
        select(DashboardWidget).where(
            DashboardWidget.widget_id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
    )
    widget = result.scalar_one_or_none()
    if widget is None:
        raise HTTPException(status_code=404, detail="ウィジェットが見つかりません")

    data = await _fetch_widget_data(session, widget)
    return {
        "widget_id": str(widget.widget_id),
        "widget_type": widget.widget_type,
        "refreshed_at": datetime.now(UTC).isoformat(),
        "data": data,
    }


# ── ウィジェット種別一覧 ───────────────────────────────────────────────────────


@router.get("/widget-types/catalog")
async def get_widget_catalog() -> list[dict]:
    """利用可能なウィジェット種別カタログ"""
    return [
        {
            "type": WidgetType.INCIDENT_COUNT,
            "name": "インシデント件数",
            "description": "期間別インシデント件数の推移",
            "chart_types": ["bar", "line"],
            "default_size": {"w": 4, "h": 3},
        },
        {
            "type": WidgetType.MTTR_TREND,
            "name": "MTTR トレンド",
            "description": "平均復旧時間のトレンド分析",
            "chart_types": ["line"],
            "default_size": {"w": 6, "h": 4},
        },
        {
            "type": WidgetType.SLA_GAUGE,
            "name": "SLA 達成率ゲージ",
            "description": "SLA 達成率をゲージで表示",
            "chart_types": ["gauge"],
            "default_size": {"w": 3, "h": 3},
        },
        {
            "type": WidgetType.CMDB_MAP,
            "name": "CMDB 資産マップ",
            "description": "構成アイテムの依存関係マップ",
            "chart_types": ["network"],
            "default_size": {"w": 8, "h": 6},
        },
        {
            "type": WidgetType.AI_ANOMALY_HEATMAP,
            "name": "AI 異常スコアヒートマップ",
            "description": "AI検知の異常スコア時系列ヒートマップ",
            "chart_types": ["heatmap"],
            "default_size": {"w": 6, "h": 4},
        },
        {
            "type": WidgetType.ACTIVITY_TIMELINE,
            "name": "アクティビティタイムライン",
            "description": "最近のインシデント・変更・問題のタイムライン",
            "chart_types": ["timeline"],
            "default_size": {"w": 12, "h": 5},
        },
        {
            "type": WidgetType.CHANGE_COUNT,
            "name": "変更件数",
            "description": "変更管理の件数・リスクレベル別分布",
            "chart_types": ["bar", "pie"],
            "default_size": {"w": 4, "h": 3},
        },
        {
            "type": WidgetType.KPI_CARD,
            "name": "KPI カード",
            "description": "単一指標をカード形式で強調表示",
            "chart_types": ["card"],
            "default_size": {"w": 3, "h": 2},
        },
    ]


# ── 内部ヘルパー ───────────────────────────────────────────────────────────────


async def _fetch_widget_data(
    session: AsyncSession, widget: DashboardWidget
) -> dict[str, Any]:
    """ウィジェット種別に応じてデータを収集"""
    from src.models.change import Change
    from src.models.incident import Incident

    wtype = widget.widget_type

    if wtype == WidgetType.INCIDENT_COUNT:
        result = await session.execute(select(Incident).limit(100))
        incidents = result.scalars().all()
        return {
            "total": len(incidents),
            "by_priority": _count_by(incidents, "priority"),
            "by_status": _count_by(incidents, "status"),
        }

    elif wtype == WidgetType.CHANGE_COUNT:
        result = await session.execute(select(Change).limit(100))
        changes = result.scalars().all()
        return {
            "total": len(changes),
            "by_status": _count_by(changes, "status"),
            "by_type": _count_by(changes, "change_type"),
        }

    elif wtype == WidgetType.SLA_GAUGE:
        result = await session.execute(select(Incident).limit(500))
        incidents = result.scalars().all()
        if not incidents:
            return {"achievement_rate": 100.0, "total": 0, "breached": 0}
        breached = sum(1 for i in incidents if getattr(i, "sla_breached", False))
        rate = round((1 - breached / len(incidents)) * 100, 1)
        return {"achievement_rate": rate, "total": len(incidents), "breached": breached}

    elif wtype == WidgetType.ACTIVITY_TIMELINE:
        result = await session.execute(
            select(Incident).order_by(Incident.created_at.desc()).limit(10)
        )
        items = [
            {
                "type": "incident",
                "id": str(i.incident_number),
                "title": i.title,
                "time": i.created_at.isoformat(),
                "priority": i.priority,
            }
            for i in result.scalars().all()
        ]
        return {"items": items}

    else:
        # MTTR_TREND / CMDB_MAP / AI_ANOMALY_HEATMAP / KPI_CARD
        return {"message": f"{wtype} データは別途計算エンジンが提供します", "data": []}


def _count_by(items: list, attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(getattr(item, attr, "unknown"))
        counts[key] = counts.get(key, 0) + 1
    return counts
