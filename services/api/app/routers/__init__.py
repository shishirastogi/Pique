from fastapi import APIRouter

from app.routers import admin, auth, content, lock, profile, sessions, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(lock.router, prefix="/lock", tags=["lock"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
