from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.assets import router as assets_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.users import router as users_router
from app.api.v1.departments import router as departments_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])
api_router.include_router(assignments_router, prefix="/assignments", tags=["assignments"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(departments_router, prefix="/departments", tags=["departments"])


