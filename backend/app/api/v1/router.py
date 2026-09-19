from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.assets import router as assets_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.users import router as users_router
from app.api.v1.departments import router as departments_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.maintenances import router as maintenances_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.assistant import router as assistant_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])
api_router.include_router(assignments_router, prefix="/assignments", tags=["assignments"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(departments_router, prefix="/departments", tags=["departments"])
api_router.include_router(incidents_router, prefix="/incidents", tags=["incidents"])
api_router.include_router(maintenances_router, prefix="/maintenances", tags=["maintenances"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(assistant_router, prefix="/assistant", tags=["assistant"])


