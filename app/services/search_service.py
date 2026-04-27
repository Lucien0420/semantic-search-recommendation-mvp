from __future__ import annotations

import math

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.post import Post
from app.schemas.post import PostReadWithScore
from app.services.embedding_service import EmbeddingService
from app.services.query_expansion import expand_search_query
from app.services.vector_db import VectorStore, distance_to_similarity_cosine


async def semantic_search(
    session: AsyncSession,
    vector_store: VectorStore,
    embedding_service: EmbeddingService,
    settings: Settings,
    http: httpx.AsyncClient | None,
    *,
    query: str,
    limit: int,
    min_score: float,
) -> list[PostReadWithScore]:
    expanded = await expand_search_query(query, settings, http)
    embedding = await embedding_service.embed(expanded)
    n_fetch = min(200, max(limit * 5, limit))
    raw = await vector_store.query_similar(embedding, n_results=n_fetch, exclude_ids=None)

    qids = (raw.get("ids") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    ranked: list[tuple[int, float]] = []
    for pid_str, dist in zip(qids, dists, strict=False):
        if dist is None:
            continue
        sim = distance_to_similarity_cosine(float(dist))
        if not math.isfinite(sim) or sim < min_score:
            continue
        ranked.append((int(pid_str), sim))

    ids = [pid for pid, _ in ranked]
    if not ids:
        return []

    stmt = select(Post).where(Post.id.in_(ids))
    rows = (await session.execute(stmt)).scalars().all()
    by_id = {p.id: p for p in rows}

    out: list[PostReadWithScore] = []
    for pid, sim in ranked:
        p = by_id.get(pid)
        if p is None:
            continue
        out.append(
            PostReadWithScore(
                id=p.id,
                content=p.content,
                author_id=p.author_id,
                tags=[str(t) for t in (p.tags or [])],
                content_type=p.content_type,
                created_at=p.created_at,
                similarity=sim,
            )
        )
        if len(out) >= limit:
            break
    return out
