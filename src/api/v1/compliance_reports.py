"""コンプライアンスレポート自動生成 API - PDF/Excel ダウンロード"""

import io
from datetime import UTC, datetime
from enum import StrEnum

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.report_generator import (
    ComplianceReportBuilder,
    ExcelReportGenerator,
    PdfReportGenerator,
    ReportData,
)

router = APIRouter(prefix="/compliance-reports", tags=["compliance-reports"])

_excel_gen = ExcelReportGenerator()
_pdf_gen = PdfReportGenerator()


class ReportType(StrEnum):
    JSOX_CHANGE = "jsox_change"
    INCIDENT_ANALYSIS = "incident_analysis"
    CMDB_INVENTORY = "cmdb_inventory"
    AUDIT_TRAIL = "audit_trail"


class OutputFormat(StrEnum):
    PDF = "pdf"
    EXCEL = "excel"


# ── レポート生成・ダウンロード ──────────────────────────────────────────────────


@router.get("/generate")
async def generate_report(
    report_type: ReportType = Query(..., description="レポート種別"),
    output_format: OutputFormat = Query(OutputFormat.EXCEL, description="出力形式"),
    year: int = Query(None, ge=2000, le=2100),
    month: int = Query(None, ge=1, le=12),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """コンプライアンスレポートを PDF または Excel 形式で生成・ダウンロード"""
    now = datetime.now(UTC)
    target_year = year or now.year
    target_month = month or now.month
    period = f"{target_year}年{target_month}月"

    report_data = await _build_report_data(
        session, report_type, period, target_year, target_month
    )

    if output_format == OutputFormat.PDF:
        content = _pdf_gen.generate(report_data)
        media_type = "application/pdf"
        ext = "pdf"
    else:
        content = _excel_gen.generate(report_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"

    filename = f"{report_type}_{target_year}{target_month:02d}.{ext}"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/preview")
async def preview_report(
    report_type: ReportType = Query(..., description="レポート種別"),
    year: int = Query(None, ge=2000, le=2100),
    month: int = Query(None, ge=1, le=12),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """レポートデータのプレビュー（JSON形式）"""
    now = datetime.now(UTC)
    target_year = year or now.year
    target_month = month or now.month
    period = f"{target_year}年{target_month}月"

    report_data = await _build_report_data(
        session, report_type, period, target_year, target_month
    )

    return {
        "title": report_data.title,
        "period": report_data.period,
        "generated_at": report_data.generated_at.isoformat(),
        "sections": [
            {
                "name": s["name"],
                "summary": s.get("summary", ""),
                "headers": s.get("headers", []),
                "row_count": len(s.get("rows", [])),
            }
            for s in report_data.sections
        ],
    }


@router.get("/types")
async def list_report_types() -> list[dict]:
    """利用可能なレポート種別一覧"""
    return [
        {
            "type": ReportType.JSOX_CHANGE,
            "name": "J-SOX 変更管理レポート",
            "description": "変更管理プロセスの J-SOX 準拠証跡レポート",
            "formats": ["pdf", "excel"],
        },
        {
            "type": ReportType.INCIDENT_ANALYSIS,
            "name": "インシデント分析レポート",
            "description": "MTTR・SLA達成率・優先度別分析レポート",
            "formats": ["pdf", "excel"],
        },
        {
            "type": ReportType.CMDB_INVENTORY,
            "name": "CMDB 資産台帳",
            "description": "構成アイテム一覧・変更履歴レポート",
            "formats": ["pdf", "excel"],
        },
        {
            "type": ReportType.AUDIT_TRAIL,
            "name": "セキュリティ監査証跡レポート",
            "description": "操作ログ・認証履歴の監査証跡",
            "formats": ["pdf", "excel"],
        },
    ]


# ── 内部ヘルパー ──────────────────────────────────────────────────────────────


async def _build_report_data(
    session: AsyncSession,
    report_type: ReportType,
    period: str,
    year: int,
    month: int,
) -> ReportData:
    """レポート種別に応じてデータを収集してReportDataを構築"""
    from calendar import monthrange
    from datetime import datetime

    _, last_day = monthrange(year, month)
    start = datetime(year, month, 1, tzinfo=UTC)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

    if report_type == ReportType.JSOX_CHANGE:
        return await _build_jsox_change(session, period, start, end)
    elif report_type == ReportType.INCIDENT_ANALYSIS:
        return await _build_incident_analysis(session, period, start, end)
    elif report_type == ReportType.CMDB_INVENTORY:
        return await _build_cmdb_inventory(session, period)
    elif report_type == ReportType.AUDIT_TRAIL:
        return await _build_audit_trail(session, period, start, end)
    else:
        raise HTTPException(status_code=400, detail=f"不明なレポート種別: {report_type}")


async def _build_jsox_change(session, period, start, end) -> ReportData:
    from src.models.change import Change

    result = await session.execute(
        select(Change).where(Change.created_at >= start, Change.created_at <= end).limit(500)
    )
    changes = [
        {
            "change_number": c.change_number,
            "title": c.title,
            "change_type": c.change_type,
            "status": c.status,
            "risk_level": c.risk_level or "N/A",
            "created_at": c.created_at.strftime("%Y-%m-%d"),
        }
        for c in result.scalars().all()
    ]
    return ComplianceReportBuilder.build_jsox_change_report(changes, period)


async def _build_incident_analysis(session, period, start, end) -> ReportData:
    from src.models.incident import Incident

    result = await session.execute(
        select(Incident).where(Incident.created_at >= start, Incident.created_at <= end).limit(500)
    )
    incidents = [
        {
            "incident_number": i.incident_number,
            "title": i.title,
            "priority": i.priority,
            "status": i.status,
            "sla_breached": i.sla_breached,
            "created_at": i.created_at.strftime("%Y-%m-%d"),
        }
        for i in result.scalars().all()
    ]
    return ComplianceReportBuilder.build_incident_analysis_report(incidents, period)


async def _build_cmdb_inventory(session, period) -> ReportData:
    from src.models.cmdb import ConfigurationItem

    result = await session.execute(select(ConfigurationItem).limit(500))
    items = [
        {
            "ci_name": c.ci_name,
            "ci_type": c.ci_type,
            "status": c.status,
            "environment": "N/A",
            "owner": str(c.owner_id) if c.owner_id else "N/A",
        }
        for c in result.scalars().all()
    ]
    return ComplianceReportBuilder.build_cmdb_inventory_report(items, period)


async def _build_audit_trail(session, period, start, end) -> ReportData:
    from src.models.audit import AuditLog

    result = await session.execute(
        select(AuditLog).where(AuditLog.created_at >= start, AuditLog.created_at <= end).limit(500)
    )
    logs = [
        {
            "action": log.action,
            "entity_type": log.resource_type or "N/A",
            "user_id": str(log.user_id) if log.user_id else "system",
            "ip_address": log.ip_address or "N/A",
            "created_at": log.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for log in result.scalars().all()
    ]
    return ComplianceReportBuilder.build_audit_trail_report(logs, period)
