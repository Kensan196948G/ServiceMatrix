"""問題管理 GraphQL 型定義"""

from datetime import datetime
from uuid import UUID

import strawberry


@strawberry.type
class ProblemType:
    id: UUID
    problem_number: str
    title: str
    description: str | None
    priority: str
    status: str
    assigned_to: UUID | None
    root_cause: str | None
    workaround: str | None
    known_error: bool
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
