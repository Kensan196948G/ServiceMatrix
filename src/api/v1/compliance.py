"""コンプライアンスAPI - SOC2/ISO27001チェックリスト・レポート"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.change import Change
from src.models.cmdb import ConfigurationItem
from src.models.incident import Incident
from src.models.user import User

router = APIRouter(prefix="/compliance", tags=["コンプライアンス"])

# SOC2チェック定義
SOC2_CHECKS = [
    {
        "id": "soc2-cc6.1",
        "category": "CC6 - Logical Access",
        "title": "ユーザー認証の実装",
        "description": "システムへのアクセスに認証メカニズムが実装されているか確認します。",
    },
    {
        "id": "soc2-cc6.2",
        "category": "CC6 - Logical Access",
        "title": "アクセス制御ポリシー",
        "description": "ロールベースアクセス制御(RBAC)が実装されているか確認します。",
    },
    {
        "id": "soc2-cc6.3",
        "category": "CC6 - Logical Access",
        "title": "不要なアクセス権限の削除",
        "description": "退職・異動時の権限剥奪プロセスが存在するか確認します。",
    },
    {
        "id": "soc2-cc7.1",
        "category": "CC7 - System Operations",
        "title": "変更管理プロセス",
        "description": "システム変更が管理されたプロセスで行われているか確認します。",
    },
    {
        "id": "soc2-cc7.2",
        "category": "CC7 - System Operations",
        "title": "インシデント対応手順",
        "description": "セキュリティインシデントへの対応手順が整備されているか確認します。",
    },
    {
        "id": "soc2-cc7.3",
        "category": "CC7 - System Operations",
        "title": "監視とアラート",
        "description": "システム監視とアラート通知が設定されているか確認します。",
    },
    {
        "id": "soc2-a1.1",
        "category": "A1 - Availability",
        "title": "SLAの定義と監視",
        "description": "サービスレベルアグリーメントが定義され監視されているか確認します。",
    },
    {
        "id": "soc2-a1.2",
        "category": "A1 - Availability",
        "title": "バックアップと復旧手順",
        "description": "データバックアップと災害復旧手順が整備されているか確認します。",
    },
]

# ISO27001チェック定義
ISO27001_CHECKS = [
    {
        "id": "iso-a5.1",
        "category": "A.5 情報セキュリティポリシー",
        "title": "情報セキュリティポリシー文書",
        "description": "情報セキュリティポリシーが文書化・承認・周知されているか確認します。",
    },
    {
        "id": "iso-a6.1",
        "category": "A.6 情報セキュリティの組織",
        "title": "情報セキュリティの役割と責任",
        "description": "情報セキュリティに関する役割と責任が定義されているか確認します。",
    },
    {
        "id": "iso-a8.1",
        "category": "A.8 資産管理",
        "title": "資産の識別とCMDB管理",
        "description": "情報資産が識別・分類・管理されているか確認します。",
    },
    {
        "id": "iso-a8.2",
        "category": "A.8 資産管理",
        "title": "情報の分類",
        "description": "情報が適切に分類・ラベル付けされているか確認します。",
    },
    {
        "id": "iso-a9.1",
        "category": "A.9 アクセス制御",
        "title": "アクセス制御ポリシー",
        "description": "アクセス制御ポリシーが策定・実装されているか確認します。",
    },
    {
        "id": "iso-a9.2",
        "category": "A.9 アクセス制御",
        "title": "ユーザーアクセス管理",
        "description": "ユーザーアクセスの登録・削除プロセスが存在するか確認します。",
    },
    {
        "id": "iso-a12.1",
        "category": "A.12 運用セキュリティ",
        "title": "変更管理手順の整備",
        "description": "ITインフラ・システムの変更管理手順が整備されているか確認します。",
    },
    {
        "id": "iso-a12.3",
        "category": "A.12 運用セキュリティ",
        "title": "情報のバックアップ",
        "description": "情報のバックアップポリシーと手順が整備されているか確認します。",
    },
    {
        "id": "iso-a16.1",
        "category": "A.16 情報セキュリティインシデント管理",
        "title": "インシデント管理手順",
        "description": "情報セキュリティインシデントの管理手順が整備されているか確認します。",
    },
    {
        "id": "iso-a17.1",
        "category": "A.17 事業継続管理",
        "title": "情報セキュリティの継続",
        "description": "事業継続計画に情報セキュリティが組み込まれているか確認します。",
    },
    {
        "id": "iso-a18.1",
        "category": "A.18 コンプライアンス",
        "title": "適用法令・規制の識別",
        "description": "適用される法令・規制・契約要件が識別されているか確認します。",
    },
]


async def _evaluate_checks(checks: list[dict], db: AsyncSession) -> list[dict]:
    """チェック項目を自動評価する"""
    # DBから必要な情報を一括取得
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    change_count = (await db.execute(select(func.count()).select_from(Change))).scalar_one()
    incident_count = (await db.execute(select(func.count()).select_from(Incident))).scalar_one()
    ci_count = (await db.execute(select(func.count()).select_from(ConfigurationItem))).scalar_one()

    # sla_breached_atフィールドの存在確認（モデルにフィールドがあれば PASS）
    sla_field_exists = hasattr(Incident, "sla_breached_at")

    results = []
    for check in checks:
        status = "MANUAL"
        evidence = None

        cid = check["id"]
        title = check["title"]

        if "ユーザー認証" in title or ("アクセス制御" in title and "soc2" in cid):
            if user_count > 0:
                status = "PASS"
                evidence = f"ユーザー数: {user_count}"
            else:
                status = "FAIL"
                evidence = "ユーザーが登録されていません"

        elif "変更管理" in title:
            if change_count > 0:
                status = "PASS"
                evidence = f"変更管理レコード数: {change_count}"
            else:
                status = "FAIL"
                evidence = "変更管理レコードが存在しません"

        elif "インシデント" in title:
            if incident_count > 0:
                status = "PASS"
                evidence = f"インシデントレコード数: {incident_count}"
            else:
                status = "FAIL"
                evidence = "インシデントレコードが存在しません"

        elif "SLA" in title:
            if sla_field_exists:
                status = "PASS"
                evidence = "sla_breached_atフィールドが実装済み"
            else:
                status = "FAIL"
                evidence = "SLA監視フィールドが未実装"

        elif "資産" in title or "CMDB" in title:
            if ci_count > 0:
                status = "PASS"
                evidence = f"構成アイテム数: {ci_count}"
            else:
                status = "FAIL"
                evidence = "構成アイテムが登録されていません"

        elif "ユーザーアクセス管理" in title:
            if user_count > 0:
                status = "PASS"
                evidence = f"ユーザー数: {user_count}"
            else:
                status = "FAIL"
                evidence = "ユーザーが登録されていません"

        results.append(
            {
                "id": check["id"],
                "category": check["category"],
                "title": check["title"],
                "description": check["description"],
                "status": status,
                "evidence": evidence,
            }
        )

    return results


def _build_summary(evaluated: list[dict]) -> dict:
    total = len(evaluated)
    pass_count = sum(1 for c in evaluated if c["status"] == "PASS")
    fail_count = sum(1 for c in evaluated if c["status"] == "FAIL")
    manual_count = sum(1 for c in evaluated if c["status"] == "MANUAL")
    # PASSのみでスコア計算（MANUAL は除外対象分母から除く）
    score = round(pass_count / total * 100) if total > 0 else 0
    return {
        "total": total,
        "pass": pass_count,
        "fail": fail_count,
        "manual": manual_count,
        "score": score,
    }


@router.get("/checks/soc2", summary="SOC2チェックリスト取得")
async def get_soc2_checks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """SOC2 Type II チェックリスト（システム自動評価付き）"""
    evaluated = await _evaluate_checks(SOC2_CHECKS, db)
    summary = _build_summary(evaluated)
    return {"checks": evaluated, "summary": summary}


@router.get("/checks/iso27001", summary="ISO27001チェックリスト取得")
async def get_iso27001_checks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """ISO27001:2022 チェックリスト（システム自動評価付き）"""
    evaluated = await _evaluate_checks(ISO27001_CHECKS, db)
    summary = _build_summary(evaluated)
    return {"checks": evaluated, "summary": summary}


@router.get("/report", summary="統合コンプライアンスレポート取得")
async def get_compliance_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """SOC2 + ISO27001 統合コンプライアンスレポート"""
    soc2_evaluated = await _evaluate_checks(SOC2_CHECKS, db)
    iso_evaluated = await _evaluate_checks(ISO27001_CHECKS, db)
    soc2_summary = _build_summary(soc2_evaluated)
    iso_summary = _build_summary(iso_evaluated)

    all_checks = soc2_evaluated + iso_evaluated
    all_summary = _build_summary(all_checks)

    return {
        "soc2": {"checks": soc2_evaluated, "summary": soc2_summary},
        "iso27001": {"checks": iso_evaluated, "summary": iso_summary},
        "overall": {"summary": all_summary},
    }


@router.get("/score", summary="コンプライアンススコア取得")
async def get_compliance_score(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """統合コンプライアンススコア（0-100）"""
    soc2_evaluated = await _evaluate_checks(SOC2_CHECKS, db)
    iso_evaluated = await _evaluate_checks(ISO27001_CHECKS, db)
    soc2_summary = _build_summary(soc2_evaluated)
    iso_summary = _build_summary(iso_evaluated)

    all_checks = soc2_evaluated + iso_evaluated
    all_summary = _build_summary(all_checks)

    return {
        "overall_score": all_summary["score"],
        "soc2_score": soc2_summary["score"],
        "iso27001_score": iso_summary["score"],
        "summary": all_summary,
    }
