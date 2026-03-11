"""APIルーター集約"""

from fastapi import APIRouter

from src.api.v1.ai import router as ai_router
from src.api.v1.analytics import router as analytics_router
from src.api.v1.audit import router as audit_router
from src.api.v1.auth import router as auth_router
from src.api.v1.backup import router as backup_router
from src.api.v1.changes import router as changes_router
from src.api.v1.cmdb import router as cmdb_router
from src.api.v1.compliance import router as compliance_router
from src.api.v1.dashboard import router as dashboard_router
from src.api.v1.health import router as health_router
from src.api.v1.incidents import router as incidents_router
from src.api.v1.integrations import router as integrations_router
from src.api.v1.maintenance import router as maintenance_router
from src.api.v1.notifications import router as notifications_router
from src.api.v1.problems import router as problems_router
from src.api.v1.reports import router as reports_router
from src.api.v1.search import router as search_router
from src.api.v1.service_catalog import router as service_catalog_router
from src.api.v1.service_requests import router as service_requests_router
from src.api.v1.sla import router as sla_router
from src.api.v1.webhooks import router as webhooks_router
from src.api.v1.websocket import router as websocket_router

api_router = APIRouter()
api_router.include_router(backup_router)
api_router.include_router(compliance_router)
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(incidents_router)
api_router.include_router(changes_router)
api_router.include_router(problems_router)
api_router.include_router(cmdb_router)
api_router.include_router(service_requests_router)
api_router.include_router(service_catalog_router)
api_router.include_router(sla_router)
api_router.include_router(webhooks_router)
api_router.include_router(audit_router)
api_router.include_router(ai_router)
api_router.include_router(websocket_router)
api_router.include_router(notifications_router)
api_router.include_router(dashboard_router)
api_router.include_router(reports_router)
api_router.include_router(search_router)
api_router.include_router(integrations_router)
api_router.include_router(maintenance_router)
api_router.include_router(analytics_router)
