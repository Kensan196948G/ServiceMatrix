"""バックアップ管理API - pg_dump/SQLiteバックアップ"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.middleware.rbac import require_role
from src.models.user import User, UserRole

router = APIRouter(prefix="/backup", tags=["バックアップ"])

BACKUP_DIR = Path("/tmp/servicematrix-backups")  # noqa: S108


def _ensure_backup_dir() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/create", summary="バックアップ作成")
async def create_backup(
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> dict:
    """データベースバックアップを作成します（PostgreSQL: pg_dump / SQLite: モック）"""
    _ensure_backup_dir()
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    filepath = BACKUP_DIR / filename

    db_url = os.getenv("DATABASE_URL", "")

    if "sqlite" in db_url or not db_url:
        # 開発/テスト環境ではモックバックアップ
        filepath.write_text(
            f"-- ServiceMatrix Mock Backup\n-- Created at: {datetime.now().isoformat()}\n"
            f"-- Database URL: {db_url or '(not set)'}\n"
        )
        stat = filepath.stat()
        return {
            "filename": filename,
            "size_bytes": stat.st_size,
            "created_at": datetime.now().isoformat(),
            "type": "mock",
        }

    # PostgreSQL環境: pg_dump実行
    result = subprocess.run(  # noqa: S603
        ["pg_dump", "-F", "p", "-f", str(filepath)],  # noqa: S607
        env={**os.environ, "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "")},
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"バックアップ失敗: {result.stderr}")

    stat = filepath.stat()
    return {
        "filename": filename,
        "size_bytes": stat.st_size,
        "created_at": datetime.now().isoformat(),
        "type": "postgresql",
    }


@router.get("/list", summary="バックアップファイル一覧")
async def list_backups(
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> dict:
    """バックアップファイルの一覧を返します"""
    _ensure_backup_dir()
    files = []
    for f in sorted(BACKUP_DIR.glob("backup_*.sql"), reverse=True):
        stat = f.stat()
        files.append(
            {
                "filename": f.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
        )
    return {"backups": files, "total": len(files)}


@router.get("/download/{filename}", summary="バックアップファイルダウンロード")
async def download_backup(
    filename: str,
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> FileResponse:
    """指定したバックアップファイルをダウンロードします"""
    # パストラバーサル対策
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    filepath = BACKUP_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="バックアップファイルが見つかりません")
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.delete("/{filename}", summary="バックアップファイル削除")
async def delete_backup(
    filename: str,
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> dict:
    """指定したバックアップファイルを削除します"""
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="無効なファイル名です")
    filepath = BACKUP_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="バックアップファイルが見つかりません")
    filepath.unlink()
    return {"message": f"{filename} を削除しました"}


@router.get("/status", summary="バックアップ設定状態")
async def get_backup_status(
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> dict:
    """バックアップ設定の状態を返します"""
    _ensure_backup_dir()
    db_url = os.getenv("DATABASE_URL", "")
    db_type = "sqlite" if ("sqlite" in db_url or not db_url) else "postgresql"

    backups = sorted(BACKUP_DIR.glob("backup_*.sql"), reverse=True)
    last_backup = None
    if backups:
        stat = backups[0].stat()
        last_backup = {
            "filename": backups[0].name,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "size_bytes": stat.st_size,
        }

    return {
        "backup_dir": str(BACKUP_DIR),
        "db_type": db_type,
        "total_backups": len(backups),
        "last_backup": last_backup,
    }
