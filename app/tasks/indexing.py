from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI

from app.core.config import get_settings
from app.database.session import AsyncSessionLocal
from app.models.post import Post
from app.services.embedding_service import EmbeddingService
from app.services.vector_db import VectorStore
from app.utils.text_for_embedding import post_to_embed_text

logger = logging.getLogger(__name__)


async def index_post_background(app: FastAPI, post_id: int) -> None:
    settings = get_settings()
    http: httpx.AsyncClient = app.state.http_client
    vector_store: VectorStore = app.state.vector_store

    try:
        async with AsyncSessionLocal() as session:
            post = await session.get(Post, post_id)
            if post is None:
                logger.error("Background index: post id=%s does not exist", post_id)
                return
            text = post_to_embed_text(post)
            pid = post.id
            author_id = post.author_id
            tags = list(post.tags or [])

        emb_svc = EmbeddingService(settings, http)
        embedding = await emb_svc.embed(text)
        await vector_store.upsert_post(
            post_id=pid,
            embedding=embedding,
            document=text,
            author_id=author_id,
            tags=tags,
        )
    except Exception:
        logger.exception("Background indexing failed post_id=%s", post_id)
