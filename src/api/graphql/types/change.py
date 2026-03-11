"""変更管理 GraphQL 型定義"""

from datetime import datetime
from uuid import UUID

import strawberry


@strawberry.type
class ChangeType:
    id: UUID
    change_number: str
    title: str
    description: str | None
    change_type: str
    status: str
    requested_by: UUID | None
    assigned_to: UUID | None
    risk_score: int
    risk_level: str | None
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    created_at: datetime
    updated_at: datetime
