from __future__ import annotations

import logging
import math
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from fastapi.concurrency import run_in_threadpool

from app.core.config import Settings

logger = logging.getLogger(__name__)


def _chroma_metadata(post_id: int, author_id: int, tags: list[Any]) -> dict[str, Any]:
    tag_str = ",".join(str(t) for t in tags) if tags else ""
    return {
        "post_id": int(post_id),
        "author_id": int(author_id),
        "tags": tag_str,
    }


class VectorStore:
    """Chroma persistence; sync Chroma calls run in a thread pool to avoid blocking the loop."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        try:
            self._client = chromadb.PersistentClient(path=settings.chroma_path)
            self._collection: Collection = self._client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.exception("ChromaDB init failed: %s", e)
            raise

    @property
    def collection_name(self) -> str:
        return self._settings.chroma_collection

    def _upsert_sync(
        self,
        post_id: int,
        embedding: list[float],
        document: str,
        author_id: int,
        tags: list[Any],
    ) -> None:
        pid = str(post_id)
        self._collection.upsert(
            ids=[pid],
            embeddings=[embedding],
            documents=[document],
            metadatas=[_chroma_metadata(post_id, author_id, tags)],
        )

    async def upsert_post(
        self,
        post_id: int,
        embedding: list[float],
        document: str,
        author_id: int,
        tags: list[Any],
    ) -> None:
        await run_in_threadpool(
            self._upsert_sync,
            post_id,
            embedding,
            document,
            author_id,
            tags,
        )

    def _query_sync(
        self,
        embedding: list[float],
        n_results: int,
        exclude_ids: set[int] | None = None,
    ) -> dict[str, Any]:
        total = self._collection.count()
        if total == 0:
            return {"ids": [[]], "distances": [[]], "documents": [[]], "metadatas": [[]]}

        ex = frozenset(exclude_ids) if exclude_ids else frozenset()
        # Avoid Chroma where/$nin (metadata typing differs across versions); over-fetch then filter
        need = max(1, n_results + len(ex))
        fetch = min(total, need)

        raw = self._collection.query(
            query_embeddings=[embedding],
            n_results=fetch,
            include=["distances", "metadatas", "documents"],
        )

        ids0 = (raw.get("ids") or [[]])[0] or []
        dists0 = (raw.get("distances") or [[]])[0] or []
        docs0 = (raw.get("documents") or [[]])[0] or []
        metas0 = (raw.get("metadatas") or [[]])[0] or []

        f_ids: list[str] = []
        f_dist: list[Any] = []
        f_docs: list[Any] = []
        f_meta: list[Any] = []

        for i, sid in enumerate(ids0):
            try:
                pid = int(sid)
            except (TypeError, ValueError):
                continue
            if pid in ex:
                continue
            f_ids.append(str(sid))
            f_dist.append(dists0[i] if i < len(dists0) else None)
            f_docs.append(docs0[i] if i < len(docs0) else None)
            f_meta.append(metas0[i] if i < len(metas0) else None)
            if len(f_ids) >= n_results:
                break

        return {
            "ids": [f_ids],
            "distances": [f_dist],
            "documents": [f_docs],
            "metadatas": [f_meta],
        }

    async def query_similar(
        self,
        embedding: list[float],
        n_results: int,
        exclude_ids: set[int] | None = None,
    ) -> dict[str, Any]:
        return await run_in_threadpool(
            self._query_sync,
            embedding,
            n_results,
            exclude_ids,
        )

    def _get_sync(self, ids: list[str]) -> dict[str, Any]:
        if not ids:
            return {"ids": [], "embeddings": [], "metadatas": []}
        return self._collection.get(
            ids=ids,
            include=["embeddings", "metadatas"],
        )

    async def get_embeddings_by_post_ids(self, post_ids: list[int]) -> dict[str, Any]:
        ids = [str(i) for i in post_ids]
        return await run_in_threadpool(self._get_sync, ids)


def distance_to_similarity_cosine(distance: float) -> float:
    """Chroma cosine space: distance = 1 - cosine_similarity。"""
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(d):
        return 0.0
    sim = 1.0 - d
    if sim < 0.0:
        return 0.0
    if sim > 1.0:
        return 1.0
    if not math.isfinite(sim):
        return 0.0
    return sim
