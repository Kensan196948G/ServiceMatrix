"""DataLoader - N+1クエリ問題を解消するバッチローダー"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.dataloader import DataLoader

from src.models.change import Change
from src.models.cmdb import ConfigurationItem
from src.models.incident import Incident
from src.models.problem import Problem


def make_incident_loader(session: AsyncSession) -> DataLoader:
    """インシデント DataLoader ファクトリ"""

    async def batch_load(ids: list[UUID]) -> list[Incident | None]:
        result = await session.execute(
            select(Incident).where(Incident.incident_id.in_(ids))
        )
        rows = result.scalars().all()
        by_id = {r.incident_id: r for r in rows}
        return [by_id.get(id_) for id_ in ids]

    return DataLoader(load_fn=batch_load)


def make_change_loader(session: AsyncSession) -> DataLoader:
    """変更 DataLoader ファクトリ"""

    async def batch_load(ids: list[UUID]) -> list[Change | None]:
        result = await session.execute(
            select(Change).where(Change.change_id.in_(ids))
        )
        rows = result.scalars().all()
        by_id = {r.change_id: r for r in rows}
        return [by_id.get(id_) for id_ in ids]

    return DataLoader(load_fn=batch_load)


def make_problem_loader(session: AsyncSession) -> DataLoader:
    """問題 DataLoader ファクトリ"""

    async def batch_load(ids: list[UUID]) -> list[Problem | None]:
        result = await session.execute(
            select(Problem).where(Problem.problem_id.in_(ids))
        )
        rows = result.scalars().all()
        by_id = {r.problem_id: r for r in rows}
        return [by_id.get(id_) for id_ in ids]

    return DataLoader(load_fn=batch_load)


def make_cmdb_loader(session: AsyncSession) -> DataLoader:
    """CMDB DataLoader ファクトリ"""

    async def batch_load(ids: list[UUID]) -> list[ConfigurationItem | None]:
        result = await session.execute(
            select(ConfigurationItem).where(ConfigurationItem.ci_id.in_(ids))
        )
        rows = result.scalars().all()
        by_id = {r.ci_id: r for r in rows}
        return [by_id.get(id_) for id_ in ids]

    return DataLoader(load_fn=batch_load)


class DataLoaderContext:
    """リクエストごとの DataLoader コンテキスト"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.incident_loader: DataLoader = make_incident_loader(session)
        self.change_loader: DataLoader = make_change_loader(session)
        self.problem_loader: DataLoader = make_problem_loader(session)
        self.cmdb_loader: DataLoader = make_cmdb_loader(session)
