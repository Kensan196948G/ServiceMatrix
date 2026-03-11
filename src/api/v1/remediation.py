"""AI自動リメディエーション API エンドポイント"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.remediation_service import RemediationService

router = APIRouter(prefix="/remediation", tags=["remediation"])
_svc = RemediationService()


# ── スキーマ ───────────────────────────────────────────────────────────────────


class RuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    match_priority: str | None = None
    match_status: str | None = None
    match_keyword: str | None = None
    min_anomaly_score: float = Field(0.0, ge=0.0, le=1.0)
    action_type: str
    action_params: str | None = None
    playbook_path: str | None = None
    requires_approval: bool = False
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)
    max_executions_per_hour: int = Field(3, ge=1, le=100)
    is_enabled: bool = True
    priority_order: int = Field(100, ge=1)


class RuleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    match_priority: str | None = None
    match_status: str | None = None
    match_keyword: str | None = None
    min_anomaly_score: float | None = None
    action_type: str | None = None
    action_params: str | None = None
    requires_approval: bool | None = None
    confidence_threshold: float | None = None
    is_enabled: bool | None = None
    priority_order: int | None = None


class TriggerRequest(BaseModel):
    incident_id: uuid.UUID
    dry_run: bool = False
    anomaly_score: float = Field(0.0, ge=0.0, le=1.0)


class ApprovalRequest(BaseModel):
    approver: str = Field(..., min_length=1, max_length=200)


# ── ルール CRUD ────────────────────────────────────────────────────────────────


@router.post("/rules", status_code=201)
async def create_rule(
    body: RuleCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """リメディエーションルールを作成"""
    rule = _svc.create_rule(session, body.model_dump())
    await session.commit()
    await session.refresh(rule)
    return {
        "rule_id": str(rule.rule_id),
        "name": rule.name,
        "action_type": rule.action_type,
        "is_enabled": rule.is_enabled,
        "created_at": rule.created_at.isoformat(),
    }


@router.get("/rules")
async def list_rules(
    enabled_only: bool = Query(True),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """リメディエーションルール一覧"""
    rules = await _svc.get_rules(session, enabled_only=enabled_only)
    return [
        {
            "rule_id": str(r.rule_id),
            "name": r.name,
            "description": r.description,
            "match_priority": r.match_priority,
            "match_status": r.match_status,
            "match_keyword": r.match_keyword,
            "min_anomaly_score": r.min_anomaly_score,
            "action_type": r.action_type,
            "requires_approval": r.requires_approval,
            "confidence_threshold": r.confidence_threshold,
            "is_enabled": r.is_enabled,
            "priority_order": r.priority_order,
        }
        for r in rules
    ]


@router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """ルール単件取得"""
    rule = await _svc.get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ルールが見つかりません")
    return {
        "rule_id": str(rule.rule_id),
        "name": rule.name,
        "description": rule.description,
        "match_priority": rule.match_priority,
        "match_status": rule.match_status,
        "match_keyword": rule.match_keyword,
        "min_anomaly_score": rule.min_anomaly_score,
        "action_type": rule.action_type,
        "action_params": rule.action_params,
        "playbook_path": rule.playbook_path,
        "requires_approval": rule.requires_approval,
        "confidence_threshold": rule.confidence_threshold,
        "max_executions_per_hour": rule.max_executions_per_hour,
        "is_enabled": rule.is_enabled,
        "priority_order": rule.priority_order,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID,
    body: RuleUpdateRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """ルール更新"""
    rule = await _svc.get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ルールが見つかりません")
    _svc.update_rule(rule, body.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(rule)
    return {"rule_id": str(rule.rule_id), "updated_at": rule.updated_at.isoformat()}


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """ルール削除"""
    rule = await _svc.get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ルールが見つかりません")
    await session.delete(rule)
    await session.commit()


# ── リメディエーション実行 ─────────────────────────────────────────────────────


@router.post("/trigger")
async def trigger_remediation(
    body: TriggerRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """インシデントに対してリメディエーションを実行"""
    from sqlalchemy import select

    from src.models.incident import Incident

    # インシデント取得
    result = await session.execute(
        select(Incident).where(Incident.incident_id == body.incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="インシデントが見つかりません")

    incident_data = {
        "priority": incident.priority,
        "status": incident.status,
        "title": incident.title,
    }

    # ルールマッチング
    rules = await _svc.get_rules(session, enabled_only=True)
    matched = _svc.match_rules(rules, incident_data, anomaly_score=body.anomaly_score)

    if not matched:
        return {
            "matched": False,
            "message": "マッチするリメディエーションルールがありませんでした",
            "incident_id": str(body.incident_id),
        }

    # 最高信頼度のルールを実行
    best_rule, confidence = matched[0]
    log = await _svc.run_remediation(
        session,
        incident_id=body.incident_id,
        rule=best_rule,
        confidence=confidence,
        dry_run=body.dry_run,
    )
    await session.commit()
    await session.refresh(log)

    return {
        "matched": True,
        "log_id": str(log.log_id),
        "rule_name": best_rule.name,
        "action_type": log.action_type,
        "status": log.status,
        "confidence_score": log.confidence_score,
        "is_dry_run": log.is_dry_run,
        "result_message": log.result_message,
        "matched_rules_count": len(matched),
    }


# ── ログ照会 ──────────────────────────────────────────────────────────────────


@router.get("/logs")
async def list_logs(
    incident_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """リメディエーションログ一覧"""
    logs = await _svc.get_logs(
        session, incident_id=incident_id, status=status, limit=limit, offset=offset
    )
    return [
        {
            "log_id": str(log.log_id),
            "incident_id": str(log.incident_id) if log.incident_id else None,
            "rule_id": str(log.rule_id) if log.rule_id else None,
            "action_type": log.action_type,
            "status": log.status,
            "confidence_score": log.confidence_score,
            "is_dry_run": log.is_dry_run,
            "result_message": log.result_message,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/logs/{log_id}")
async def get_log(
    log_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """ログ単件取得"""
    log = await _svc.get_log(session, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="ログが見つかりません")
    return {
        "log_id": str(log.log_id),
        "incident_id": str(log.incident_id) if log.incident_id else None,
        "rule_id": str(log.rule_id) if log.rule_id else None,
        "action_type": log.action_type,
        "action_params": log.action_params,
        "status": log.status,
        "confidence_score": log.confidence_score,
        "is_dry_run": log.is_dry_run,
        "result_message": log.result_message,
        "error_message": log.error_message,
        "duration_ms": log.duration_ms,
        "approved_by": log.approved_by,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        "created_at": log.created_at.isoformat(),
    }


@router.post("/logs/{log_id}/approve")
async def approve_remediation(
    log_id: uuid.UUID,
    body: ApprovalRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """承認待ちリメディエーションを承認・実行"""
    log = await _svc.get_log(session, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="ログが見つかりません")
    try:
        log = await _svc.approve_remediation(session, log, body.approver)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await session.commit()
    await session.refresh(log)
    return {
        "log_id": str(log.log_id),
        "status": log.status,
        "approved_by": log.approved_by,
        "result_message": log.result_message,
    }
