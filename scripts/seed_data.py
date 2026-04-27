"""
Seed demo posts (tech / cooking / fitness) into SQLite and Chroma.

From project root:
  python scripts/seed_data.py

Requires a working embedding backend (default: Ollama + nomic-embed-text).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import chromadb
import httpx
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


POSTS_SEED: list[tuple[str, int, list[str], str]] = [
    # Tech
    (
        "Tried a new TypeScript 5 project template; strict mode saves a lot of debugging time.",
        1,
        ["tech", "dev"],
        "text",
    ),
    (
        "When training a small LM on a GPU, how do you trade off batch size vs gradient accumulation?",
        2,
        ["tech", "ai"],
        "text",
    ),
    (
        "FastAPI + SQLAlchemy 2 async APIs have been more stable than I expected.",
        1,
        ["tech", "backend"],
        "text",
    ),
    (
        "Chroma persisting locally means vectors survive restarts; nice for dev workflow.",
        3,
        ["tech", "vector-search"],
        "text",
    ),
    (
        "Rust's borrow checker was painful at first, then it became a comfort.",
        2,
        ["tech", "rust"],
        "text",
    ),
    (
        "Switched CI from GitHub Actions to a self-hosted runner; build time dropped ~30%.",
        3,
        ["tech", "devops"],
        "text",
    ),
    (
        "Edge inference latency beats the cloud, but you still need to validate quantized accuracy.",
        1,
        ["tech", "edge"],
        "text",
    ),
    (
        "A partial index in PostgreSQL on a hot query path made a big difference.",
        2,
        ["tech", "database"],
        "text",
    ),
    # Cooking
    (
        "Red wine beef stew: low oven first, then reduce; meat came out very tender.",
        4,
        ["cooking", "beef"],
        "text",
    ),
    (
        "Al dente pasta is all about salting the water and timing; I skip the cold rinse.",
        5,
        ["cooking", "pasta"],
        "text",
    ),
    (
        "Third sourdough bake finally had a decent ear; temperature control mattered most.",
        4,
        ["cooking", "baking"],
        "text",
    ),
    (
        "Thai basil pork: balance fish sauce and lime; jasmine rice is the right pairing.",
        6,
        ["cooking", "thai"],
        "text",
    ),
    (
        "Sushi rice ratio I keep fixed: rice : vinegar : sugar : salt = 5:1:0.3:0.15.",
        5,
        ["cooking", "japanese"],
        "text",
    ),
    (
        "Cast-iron steak: pat dry, high heat sear, then butter, garlic, rosemary off heat.",
        6,
        ["cooking", "steak"],
        "text",
    ),
    (
        "For braising spices, I dry-toast the pack first; aroma comes through better.",
        4,
        ["cooking", "braise"],
        "text",
    ),
    # Fitness
    (
        "Squat hinge pattern finally clicks; knee tracking feels much more stable.",
        7,
        ["fitness", "squat"],
        "text",
    ),
    (
        "After four weeks of zone-2 running, same pace with lower heart rate.",
        8,
        ["fitness", "running"],
        "text",
    ),
    (
        "Pull-ups moved from band assist to light weight; back width actually changed.",
        7,
        ["fitness", "pull-up"],
        "text",
    ),
    (
        "Split protein evenly across meals; recovery felt better subjectively.",
        8,
        ["fitness", "nutrition"],
        "text",
    ),
    (
        "Before deadlifts, bracing with breath; much less low-back stress.",
        9,
        ["fitness", "deadlift"],
        "text",
    ),
    (
        "Freestyle kick with a board; body position stays higher in the water.",
        9,
        ["fitness", "swimming"],
        "text",
    ),
    (
        "Downward dog: shift load to hamstrings; wrists feel better.",
        10,
        ["fitness", "yoga"],
        "text",
    ),
    (
        "Block periodization: heavy days vs easy cardio on separate days; fatigue is easier to manage.",
        10,
        ["fitness", "periodization"],
        "text",
    ),
]


async def main() -> None:
    from app.core.config import get_settings
    from app.database.base import Base
    from app.database.session import AsyncSessionLocal, engine
    from app.models.post import Post
    from app.models.user import User
    from app.services.embedding_service import EmbeddingService
    from app.services.passwords import hash_password
    from app.services.vector_db import VectorStore
    from app.utils.text_for_embedding import post_to_embed_text

    settings = get_settings()
    Path("data").mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    client = chromadb.PersistentClient(path=settings.chroma_path)
    try:
        client.delete_collection(settings.chroma_collection)
    except Exception:
        pass

    vector_store = VectorStore(settings)
    author_ids = sorted({t[1] for t in POSTS_SEED})
    async with httpx.AsyncClient(timeout=120.0) as http:
        emb = EmbeddingService(settings, http)

        async with AsyncSessionLocal() as session:
            for aid in author_ids:
                session.add(
                    User(
                        email=f"seed{aid}@example.com",
                        hashed_password=hash_password("Seedpass1"),
                    )
                )
            await session.flush()

            for content, author_id, tags, ctype in POSTS_SEED:
                session.add(
                    Post(
                        content=content,
                        author_id=author_id,
                        tags=tags,
                        content_type=ctype,
                    )
                )
            await session.commit()

            res = await session.execute(select(Post).order_by(Post.id))
            posts = list(res.scalars().all())

        for post in posts:
            text = post_to_embed_text(post)
            vec = await emb.embed(text)
            await vector_store.upsert_post(
                post_id=post.id,
                embedding=vec,
                document=text,
                author_id=post.author_id,
                tags=list(post.tags or []),
            )

    await engine.dispose()
    print(
        f"Seeded {len(author_ids)} demo users (seed1@example.com … password Seedpass1) and "
        f"{len(POSTS_SEED)} posts into SQLite and Chroma (collection={settings.chroma_collection})."
    )


if __name__ == "__main__":
    asyncio.run(main())
