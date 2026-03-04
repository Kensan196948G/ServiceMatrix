"""GraphQL 型定義"""

import uuid
from datetime import datetime

import strawberry


@strawberry.type
class IncidentType:
    id: uuid.UUID
    incident_number: str
    title: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime | None = None


@strawberry.type
class ChangeRequestType:
    id: uuid.UUID
    change_number: str
    title: str
    status: str
    risk_score: int | None = None
    created_at: datetime


@strawberry.type
class CMDBItemType:
    id: uuid.UUID
    name: str
    ci_type: str
    status: str
    created_at: datetime


@strawberry.type
class UserType:
    id: uuid.UUID
    username: str
    email: str
    role: str


@strawberry.type
class PaginatedIncidents:
    items: list[IncidentType]
    total: int
    limit: int
    offset: int


@strawberry.type
class NotificationType:
    success: bool
    message: str
