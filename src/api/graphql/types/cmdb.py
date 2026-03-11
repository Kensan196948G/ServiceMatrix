"""CMDB GraphQL 型定義"""

from datetime import datetime
from uuid import UUID

import strawberry


@strawberry.type
class CmdbItemType:
    id: UUID
    ci_number: str
    name: str
    ci_type: str
    ci_class: str | None
    status: str
    owner_id: UUID | None
    description: str | None
    created_at: datetime
    updated_at: datetime
