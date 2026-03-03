"""CMDB構成管理サービス"""

import uuid
from collections import deque
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.cmdb import CIRelationship, ConfigurationItem
from src.services import audit_service

logger = get_logger(__name__)


async def create_ci(db: AsyncSession, data: dict[str, Any]) -> ConfigurationItem:
    ci = ConfigurationItem(**data)
    db.add(ci)
    await db.flush()
    await db.refresh(ci)
    await audit_service.record_audit_log(
        db,
        action="CI_CREATE",
        resource_type="ConfigurationItem",
        resource_id=str(ci.ci_id),
        new_values={"ci_name": ci.ci_name, "ci_type": ci.ci_type},
    )
    logger.info("ci_created", ci_id=str(ci.ci_id), ci_name=ci.ci_name)
    return ci


async def get_cis(
    db: AsyncSession,
    ci_type: str | None,
    status: str | None,
    skip: int,
    limit: int,
) -> tuple[list[ConfigurationItem], int]:
    query = select(ConfigurationItem)
    if ci_type:
        query = query.where(ConfigurationItem.ci_type == ci_type)
    if status:
        query = query.where(ConfigurationItem.status == status)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset(skip).limit(limit).order_by(ConfigurationItem.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_ci(db: AsyncSession, ci_id: uuid.UUID) -> ConfigurationItem | None:
    result = await db.execute(select(ConfigurationItem).where(ConfigurationItem.ci_id == ci_id))
    return result.scalar_one_or_none()


async def update_ci(
    db: AsyncSession, ci_id: uuid.UUID, data: dict[str, Any]
) -> ConfigurationItem | None:
    ci = await get_ci(db, ci_id)
    if not ci:
        return None

    old_values = {k: getattr(ci, k) for k in data}
    for field, value in data.items():
        setattr(ci, field, value)
    await db.flush()
    await db.refresh(ci)
    await audit_service.record_audit_log(
        db,
        action="CI_UPDATE",
        resource_type="ConfigurationItem",
        resource_id=str(ci.ci_id),
        old_values={k: str(v) for k, v in old_values.items()},
        new_values={k: str(v) for k, v in data.items()},
    )
    return ci


async def create_ci_relationship(db: AsyncSession, data: dict[str, Any]) -> CIRelationship:
    if data.get("source_ci_id") == data.get("target_ci_id"):
        raise ValueError("source_ci_id と target_ci_id に同じCIは指定できません")

    rel = CIRelationship(**data)
    db.add(rel)
    await db.flush()
    await db.refresh(rel)
    logger.info(
        "ci_relationship_created",
        relationship_id=str(rel.relationship_id),
        relationship_type=rel.relationship_type,
    )
    return rel


async def get_ci_relationships(db: AsyncSession, ci_id: uuid.UUID) -> list[CIRelationship]:
    result = await db.execute(
        select(CIRelationship).where(
            or_(
                CIRelationship.source_ci_id == ci_id,
                CIRelationship.target_ci_id == ci_id,
            )
        )
    )
    return list(result.scalars().all())


async def analyze_impact(db: AsyncSession, ci_id: uuid.UUID) -> dict:
    result = await db.execute(select(CIRelationship).where(CIRelationship.source_ci_id == ci_id))
    outgoing = list(result.scalars().all())

    direct_target_ids = [r.target_ci_id for r in outgoing]
    direct_dependents: list[ConfigurationItem] = []
    for tid in direct_target_ids:
        ci = await get_ci(db, tid)
        if ci:
            direct_dependents.append(ci)

    visited: set[uuid.UUID] = set(direct_target_ids)
    queue = list(direct_target_ids)
    while queue:
        current_id = queue.pop(0)
        sub_result = await db.execute(
            select(CIRelationship).where(CIRelationship.source_ci_id == current_id)
        )
        for rel in sub_result.scalars().all():
            if rel.target_ci_id not in visited:
                visited.add(rel.target_ci_id)
                queue.append(rel.target_ci_id)

    ci = await get_ci(db, ci_id)
    return {
        "ci_id": ci_id,
        "ci_name": ci.ci_name if ci else "",
        "direct_dependents": direct_dependents,
        "transitive_count": len(visited),
    }


async def get_graph(
    db: AsyncSession,
    ci_type: str | None = None,
    status: str | None = None,
) -> dict:
    """全CIとその関係をグラフ構造で返す"""
    ci_query = select(ConfigurationItem)
    if ci_type:
        ci_query = ci_query.where(ConfigurationItem.ci_type == ci_type)
    if status:
        ci_query = ci_query.where(ConfigurationItem.status == status)
    ci_result = await db.execute(ci_query)
    cis = list(ci_result.scalars().all())

    ci_id_set = {ci.ci_id for ci in cis}

    rel_result = await db.execute(select(CIRelationship))
    all_rels = list(rel_result.scalars().all())
    # フィルタ適用時はノードに含まれるCI間のエッジのみ返す
    edges = [r for r in all_rels if r.source_ci_id in ci_id_set and r.target_ci_id in ci_id_set]

    nodes = [
        {
            "id": str(ci.ci_id),
            "label": ci.ci_name,
            "ci_type": ci.ci_type,
            "status": ci.status,
            "attributes": ci.attributes,
        }
        for ci in cis
    ]
    edge_list = [
        {
            "id": str(r.relationship_id),
            "source": str(r.source_ci_id),
            "target": str(r.target_ci_id),
            "relationship_type": r.relationship_type,
        }
        for r in edges
    ]

    return {
        "nodes": nodes,
        "edges": edge_list,
        "total_nodes": len(nodes),
        "total_edges": len(edge_list),
    }


async def get_ci_graph(db: AsyncSession, ci_id: uuid.UUID, depth: int = 3) -> dict:
    """特定CIを起点とした依存グラフをdepth階層まで展開（BFS）"""
    visited_ids: set[uuid.UUID] = {ci_id}
    queue: deque[tuple[uuid.UUID, int]] = deque([(ci_id, 0)])
    collected_rels: list[CIRelationship] = []

    while queue:
        current_id, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        # 双方向でRelationshipを取得
        result = await db.execute(
            select(CIRelationship).where(
                or_(
                    CIRelationship.source_ci_id == current_id,
                    CIRelationship.target_ci_id == current_id,
                )
            )
        )
        rels = list(result.scalars().all())
        for rel in rels:
            collected_rels.append(rel)
            neighbor = rel.target_ci_id if rel.source_ci_id == current_id else rel.source_ci_id
            if neighbor not in visited_ids:
                visited_ids.add(neighbor)
                queue.append((neighbor, current_depth + 1))

    # 収集したCI情報を取得
    nodes = []
    for cid in visited_ids:
        ci = await get_ci(db, cid)
        if ci:
            nodes.append(
                {
                    "id": str(ci.ci_id),
                    "label": ci.ci_name,
                    "ci_type": ci.ci_type,
                    "status": ci.status,
                    "attributes": ci.attributes,
                }
            )

    # 重複エッジ排除
    seen_rel_ids: set[uuid.UUID] = set()
    unique_edges = []
    for r in collected_rels:
        if r.relationship_id not in seen_rel_ids:
            seen_rel_ids.add(r.relationship_id)
            unique_edges.append(
                {
                    "id": str(r.relationship_id),
                    "source": str(r.source_ci_id),
                    "target": str(r.target_ci_id),
                    "relationship_type": r.relationship_type,
                }
            )

    return {
        "nodes": nodes,
        "edges": unique_edges,
        "total_nodes": len(nodes),
        "total_edges": len(unique_edges),
    }


async def get_upstream_cis(db: AsyncSession, ci_id: uuid.UUID) -> list[ConfigurationItem]:
    """このCIに依存している上流CI（incoming）を返す"""
    result = await db.execute(select(CIRelationship).where(CIRelationship.target_ci_id == ci_id))
    incoming_rels = list(result.scalars().all())

    upstream: list[ConfigurationItem] = []
    for rel in incoming_rels:
        ci = await get_ci(db, rel.source_ci_id)
        if ci:
            upstream.append(ci)
    return upstream


async def batch_impact_analysis(db: AsyncSession, ci_ids: list[uuid.UUID]) -> dict:
    """複数CIの影響分析を一括実行"""
    items = []
    all_affected: set[uuid.UUID] = set()
    for cid in ci_ids:
        result = await analyze_impact(db, cid)
        items.append(result)
        # 直接依存CIのIDを集計
        for dep in result["direct_dependents"]:
            all_affected.add(dep.ci_id)
        # 推移的影響はtransitive_countのみで返されるため、
        # ユニーク集計は直接依存 + analyze_impact内の全visited分で近似
        # 正確に集計するには再BFSが必要だが、ここでは効率のため
        # 各CIのBFS結果をマージする
    # 再度正確な集計: 各CIから到達可能な全CIをユニーク集計
    all_affected_precise: set[uuid.UUID] = set()
    for cid in ci_ids:
        impact = await _collect_transitive_ids(db, cid)
        all_affected_precise.update(impact)

    return {
        "items": items,
        "total_affected": len(all_affected_precise),
    }


async def _collect_transitive_ids(db: AsyncSession, ci_id: uuid.UUID) -> set[uuid.UUID]:
    """ci_idから推移的に到達可能な全CIのIDを返す（ヘルパー）"""
    result = await db.execute(select(CIRelationship).where(CIRelationship.source_ci_id == ci_id))
    outgoing = list(result.scalars().all())
    visited: set[uuid.UUID] = {r.target_ci_id for r in outgoing}
    queue = deque(visited)
    while queue:
        current_id = queue.popleft()
        sub_result = await db.execute(
            select(CIRelationship).where(CIRelationship.source_ci_id == current_id)
        )
        for rel in sub_result.scalars().all():
            if rel.target_ci_id not in visited:
                visited.add(rel.target_ci_id)
                queue.append(rel.target_ci_id)
    return visited
