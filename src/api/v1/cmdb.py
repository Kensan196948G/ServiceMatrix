"""CMDB構成管理API"""

import csv
import io
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.user import User, UserRole
from src.schemas.cmdb import (
    CICreate,
    CIRelationshipCreate,
    CIRelationshipResponse,
    CIResponse,
    CIUpdate,
    ImpactAnalysisResponse,
)
from src.services import cmdb_service

router = APIRouter(prefix="/cmdb", tags=["cmdb"])


@router.get("/cis", response_model=list[CIResponse])
async def list_cis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    ci_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    department: str | None = Query(default=None),
):
    items, _ = await cmdb_service.get_cis(db, ci_type, status_filter, skip, limit, department)
    return items


@router.post("/cis", response_model=CIResponse, status_code=status.HTTP_201_CREATED)
async def create_ci(
    data: CICreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.create_ci(db, data.model_dump(exclude_none=True))
    return ci


@router.get("/cis/{ci_id}", response_model=CIResponse)
async def get_ci(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.get_ci(db, ci_id)
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return ci


@router.patch("/cis/{ci_id}", response_model=CIResponse)
async def update_ci(
    ci_id: uuid.UUID,
    data: CIUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.update_ci(db, ci_id, data.model_dump(exclude_none=True))
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return ci


@router.get("/cis/{ci_id}/relationships", response_model=list[CIRelationshipResponse])
async def get_ci_relationships(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return await cmdb_service.get_ci_relationships(db, ci_id)


@router.post(
    "/relationships",
    response_model=CIRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ci_relationship(
    data: CIRelationshipCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        rel = await cmdb_service.create_ci_relationship(db, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return rel


@router.get("/cis/{ci_id}/impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    ci_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ci = await cmdb_service.get_ci(db, ci_id)
    if not ci:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIが見つかりません")
    return await cmdb_service.analyze_impact(db, ci_id)


class CIImportResult(BaseModel):
    created: int
    failed: int
    errors: list[str]


@router.get("/export", summary="CI一括エクスポート（CSV/JSON）")
async def export_cis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    format: str = Query(default="json", pattern="^(csv|json)$"),
) -> Response:
    """全CIをCSVまたはJSON形式でエクスポートする"""
    cis, _ = await cmdb_service.get_cis(db, None, None, 0, 10000)

    if format == "csv":
        output = io.StringIO()
        fieldnames = ["ci_id", "ci_name", "ci_type", "ci_class", "status", "version", "description"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for ci in cis:
            writer.writerow(
                {
                    "ci_id": str(ci.ci_id),
                    "ci_name": ci.ci_name,
                    "ci_type": ci.ci_type,
                    "ci_class": ci.ci_class or "",
                    "status": ci.status,
                    "version": ci.version or "",
                    "description": ci.description or "",
                }
            )
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cmdb_export.csv"},
        )
    else:
        data = [
            {
                "ci_id": str(ci.ci_id),
                "ci_name": ci.ci_name,
                "ci_type": ci.ci_type,
                "ci_class": ci.ci_class,
                "status": ci.status,
                "version": ci.version,
                "description": ci.description,
            }
            for ci in cis
        ]
        return Response(
            content=json.dumps(data, ensure_ascii=False, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=cmdb_export.json"},
        )


@router.post("/import", response_model=CIImportResult, summary="CI一括インポート（CSV/JSON）")
async def import_cis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.SERVICE_MANAGER)),
    ],
    file: UploadFile = File(...),
) -> CIImportResult:
    """CSV/JSONファイルからCI一括登録"""
    content = await file.read()
    created = 0
    failed = 0
    errors: list[str] = []

    try:
        filename = file.filename or ""
        if filename.endswith(".json"):
            rows = json.loads(content)
        else:
            text = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)

        for row in rows:
            try:
                ci_data: dict = {
                    "ci_name": row.get("ci_name") or row.get("name") or "",
                    "ci_type": row.get("ci_type") or "Server",
                    "status": row.get("status") or "Active",
                    "description": row.get("description") or None,
                }
                if row.get("ci_class"):
                    ci_data["ci_class"] = row["ci_class"]
                if row.get("version"):
                    ci_data["version"] = row["version"]
                if not ci_data["ci_name"]:
                    errors.append(f"CI名が空: {row}")
                    failed += 1
                    continue
                await cmdb_service.create_ci(db, ci_data)
                created += 1
            except Exception as e:
                errors.append(str(e))
                failed += 1
    except Exception as e:
        errors.append(f"ファイル解析エラー: {e}")

    return CIImportResult(created=created, failed=failed, errors=errors[:10])
