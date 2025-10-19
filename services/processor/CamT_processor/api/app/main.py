from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oi_core.db import engine, init_db

from .core.config import get_settings
from .routers import admin, events, media, persons, settings as settings_router, vehicles


def create_app() -> FastAPI:
    if engine.url.get_backend_name().startswith("sqlite"):
        init_db()
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.include_router(admin.router)
    app.include_router(persons.router)
    app.include_router(vehicles.router)
    app.include_router(events.router)
    app.include_router(media.router)
    app.include_router(settings_router.router)
    return app


app = create_app()
