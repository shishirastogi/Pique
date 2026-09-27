"""FocusWarmup API — vertical slice (docs/07-backend-api.md subset)."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import ApiError
from app.db import init_db
from app.routers import api_router

log = logging.getLogger("pique")


def create_app() -> FastAPI:
    app = FastAPI(title="FocusWarmup API", version="0.1.0-slice")

    app.add_middleware(
        CORSMiddleware,  # dev: vite proxy covers it; native shell later — keep permissive locally
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status,
                            content={"error": {"code": exc.code, "message": exc.message,
                                               "details": exc.details}})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        # keep the error envelope even for bugs (docs/07 §3) + server-side traceback
        log.exception("unhandled %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=500,
                            content={"error": {
                                "code": "INTERNAL",
                                "message": "Server error — check the API console for the stack trace.",
                                "details": None}})

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    init_db()
    app.include_router(api_router)
    _start_seed_if_empty()
    return app


def _start_seed_if_empty() -> None:
    """Cold-start guard: seed starter topics in a background thread so a fresh
    install's first sessions have real content (prefetch, docs/08 §8).
    No-op when providers are disabled (tests) or the pool is already warm."""
    import threading
    from sqlalchemy import func, select

    def run() -> None:
        from app.db import SessionLocal
        from app.models import Content
        from app.providers import enabled_providers
        from app.services import ingestion

        if not enabled_providers():
            return
        db = SessionLocal()
        try:
            if db.scalar(select(func.count(Content.id))) < 50:
                for topic in ("science", "physics", "biology", "mathematics",
                              "computer science", "history", "art", "design"):
                    ingestion.ingest_topic(db, topic, per_provider=8)
        finally:
            db.close()

    threading.Thread(target=run, daemon=True, name="startup-seed").start()


app = create_app()
