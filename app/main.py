"""Application entrypoint: wiring only. Domain logic lives in services."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError as PydanticValidationError

from app.config import settings
from app.database import SessionLocal, init_db, seed_if_empty
from app.http import failure
from app.routers.patients import router as patients_router
from app.routers.voice import router as voice_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    logger.info("startup complete env=%s db=%s", settings.app_env, settings.database_url)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(patients_router)
app.include_router(voice_router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
If STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
