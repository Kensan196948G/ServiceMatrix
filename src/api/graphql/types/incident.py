"""インシデント GraphQL 型定義"""

from datetime import datetime
from uuid import UUID

import strawberry


@strawberry.type
class IncidentType:
    id: UUID
    incident_number: str
    title: str
    description: str | None
    priority: str
    status: str
    reported_by: UUID | None
    assigned_to: UUID | None
    sla_response_due_at: datetime | None
    sla_resolution_due_at: datetime | None
    sla_breached: bool
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
