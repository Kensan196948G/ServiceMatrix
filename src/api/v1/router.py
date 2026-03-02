"""APIルーター集約"""
from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)

# Wave 2 完了後に追加予定:
# from src.api.v1.incidents import router as incidents_router
# from src.api.v1.changes import router as changes_router
# api_router.include_router(incidents_router, prefix="/incidents")
# api_router.include_router(changes_router, prefix="/changes")
