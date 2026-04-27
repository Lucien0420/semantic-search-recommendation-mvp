from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.api import api_router
from app.core.config import get_settings
from app.database.base import Base
from app.database.session import engine
from app.services.vector_db import VectorStore


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)

    Path("data").mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)

    from app import models as _orm_models  # noqa: F401 — register ORM models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    http = httpx.AsyncClient(timeout=120.0)
    app.state.http_client = http
    app.state.vector_store = await run_in_threadpool(lambda: VectorStore(settings))

    yield

    await http.aclose()
    await engine.dispose()


app = FastAPI(title="Semantic Search & Recommendation MVP", lifespan=lifespan)
app.include_router(api_router)

_DEMO_HTML = Path(__file__).resolve().parent / "static" / "demo.html"


@app.get("/demo", include_in_schema=False)
async def demo_ui() -> FileResponse:
    """Serve the single-file vanilla JS demo (same origin; no CORS)."""
    if not _DEMO_HTML.is_file():
        raise HTTPException(
            status_code=404, detail="Demo UI missing (static/demo.html not found)"
        )
    return FileResponse(_DEMO_HTML, media_type="text/html; charset=utf-8")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
