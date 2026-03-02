"""APIルーター集約"""
from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.changes import router as changes_router
from src.api.v1.cmdb import router as cmdb_router
from src.api.v1.health import router as health_router
from src.api.v1.incidents import router as incidents_router
from src.api.v1.problems import router as problems_router
from src.api.v1.service_requests import router as service_requests_router
from src.api.v1.sla import router as sla_router
from src.api.v1.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(incidents_router)
api_router.include_router(changes_router)
api_router.include_router(problems_router)
api_router.include_router(cmdb_router)
api_router.include_router(service_requests_router)
api_router.include_router(sla_router)
api_router.include_router(webhooks_router)
