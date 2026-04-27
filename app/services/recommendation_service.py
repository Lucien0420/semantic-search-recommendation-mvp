from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.user_action import UserAction
from app.schemas.post import PostReadWithScore
from app.services.vector_db import VectorStore, distance_to_similarity_cosine

logger = logging.getLogger(__name__)

LIKE = "like"
VIEW = "view"


def _chroma_get_embedding_rows(emb: Any) -> list[Any]:
    """Normalize Chroma get() embeddings: may be a list or (n, dim) ndarray; do not use `or []` on ndarrays."""
    if emb is None:
        return []
    if isinstance(emb, list):
        return emb
    arr = np.asarray(emb, dtype=float)
    if arr.size == 0:
        return []
    if arr.ndim == 2:
        return [arr[i] for i in range(arr.shape[0])]
    if arr.ndim == 1:
        return [arr]
    return []


def _vector_to_float_list(e: Any) -> list[float]:
    if e is None:
        return []
    if hasattr(e, "tolist"):
        return [float(x) for x in e.tolist()]
    return [float(x) for x in e]


def _mean_l2_normalize(vectors: Sequence[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    acc = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            acc[i] += float(x)
    n = float(len(vectors))
    mean = [x / n for x in acc]
    norm = math.sqrt(sum(x * x for x in mean))
    if norm <= 0.0:
        return mean
    return [x / norm for x in mean]


async def _excluded_post_ids_for_user(session: AsyncSession, user_id: int) -> set[int]:
    stmt = select(UserAction.post_id).where(
        UserAction.user_id == user_id,
        UserAction.action_type.in_((LIKE, VIEW)),
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {int(x) for x in rows}


async def _latest_liked_post_ids(session: AsyncSession, user_id: int, limit: int) -> list[int]:
    stmt = (
        select(UserAction.post_id)
        .where(UserAction.user_id == user_id, UserAction.action_type == LIKE)
        .order_by(UserAction.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [int(x) for x in rows]


async def _load_posts_map(session: AsyncSession, ids: list[int]) -> dict[int, Post]:
    if not ids:
        return {}
    stmt = select(Post).where(Post.id.in_(ids))
    rows = (await session.execute(stmt)).scalars().all()
    return {p.id: p for p in rows}


async def recommend_for_user(
    session: AsyncSession,
    vector_store: VectorStore,
    *,
    user_id: int,
    limit: int,
    min_score: float,
    like_window: int = 10,
    fetch_multiplier: int = 5,
) -> list[PostReadWithScore]:
    liked_ids = await _latest_liked_post_ids(session, user_id, like_window)
    if not liked_ids:
        return []

    raw = await vector_store.get_embeddings_by_post_ids(liked_ids)
    ids_raw = raw.get("ids")
    if ids_raw is None:
        ids_raw = []
    else:
        ids_raw = list(ids_raw)

    embeddings = _chroma_get_embedding_rows(raw.get("embeddings"))

    vectors: list[list[float]] = []
    for i, e in enumerate(embeddings):
        if e is None:
            logger.warning(
                "Chroma missing embedding for post id=%s, skipping",
                ids_raw[i] if i < len(ids_raw) else "?",
            )
            continue
        vec = _vector_to_float_list(e)
        if not vec:
            continue
        vectors.append(vec)

    if not vectors:
        logger.warning("No usable vectors in store for user %s liked posts", user_id)
        return []

    centroid = _mean_l2_normalize(vectors)
    if not centroid or not all(math.isfinite(x) for x in centroid):
        logger.warning("Invalid interest vector (non-finite); cannot recommend for user_id=%s", user_id)
        return []

    excluded = await _excluded_post_ids_for_user(session, user_id)
    n_fetch = min(200, max(limit * fetch_multiplier, limit + len(excluded)))

    q = await vector_store.query_similar(centroid, n_results=n_fetch, exclude_ids=excluded)

    qids = (q.get("ids") or [[]])[0]
    dists = (q.get("distances") or [[]])[0]

    ranked: list[tuple[int, float]] = []
    for pid_str, dist in zip(qids, dists, strict=False):
        if dist is None:
            continue
        sim = distance_to_similarity_cosine(float(dist))
        if not math.isfinite(sim) or sim < min_score:
            continue
        ranked.append((int(pid_str), sim))

    post_ids = [pid for pid, _ in ranked]
    posts_map = await _load_posts_map(session, post_ids)

    filled: list[PostReadWithScore] = []
    for pid, sim in ranked:
        p = posts_map.get(pid)
        if p is None:
            continue
        filled.append(
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
        if len(filled) >= limit:
            break
    return filled
