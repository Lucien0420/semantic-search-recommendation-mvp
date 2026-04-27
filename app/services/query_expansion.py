"""Query expansion: dictionary (default) + optional Ollama LLM."""

from __future__ import annotations

import logging
import re

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Substring match → extra semantic hints (small MVP table; can move to file or DB later)
_DICT_HINTS: list[tuple[str, str]] = [
    ("squat", "fitness strength legs form"),
    ("deadlift", "fitness strength back form"),
    ("pull-up", "fitness back upper body"),
    ("pull up", "fitness back upper body"),
    ("running", "fitness cardio heart rate pace"),
    ("swimming", "fitness cardio breathing"),
    ("yoga", "fitness mobility core stretch"),
    ("protein", "fitness nutrition diet"),
    ("braise", "cooking spices simmer"),
    ("steak", "cooking beef pan sear"),
    ("pasta", "cooking noodles italian"),
    ("sourdough", "cooking baking bread"),
    ("thai", "cooking southeast asia"),
    ("sushi", "cooking japanese rice"),
    ("gpu", "tech ml hardware"),
    ("typescript", "tech programming frontend"),
    ("fastapi", "tech backend python"),
    ("chromadb", "tech vector database"),
    ("postgresql", "tech database sql"),
]


def _dict_expand(query: str) -> str:
    q = query.strip()
    if not q:
        return q
    hints: list[str] = []
    lower = q.lower()
    for needle, hint in _DICT_HINTS:
        if needle.lower() in lower or needle in q:
            hints.append(hint)
    if not hints:
        return q
    merged = " ".join(dict.fromkeys(" ".join(hints).split()))  # dedupe, keep order
    return f"{q}\nRelated terms: {merged}"


def _sanitize_llm_line(text: str) -> str:
    text = text.strip().splitlines()[0] if text else ""
    text = re.sub(r"[`\"'「」]", "", text)
    return text[:200]


async def _ollama_expand(query: str, settings: Settings, http: httpx.AsyncClient) -> str:
    model = settings.ollama_expand_model.strip()
    if not model:
        return _dict_expand(query)
    base = settings.ollama_base_url.rstrip("/")
    prompt = (
        "You expand short search queries. Given the user query, output a single line only: "
        "5–8 space-separated related English terms. No punctuation, no explanation, no numbering.\n\n"
        f"Query: {query.strip()}"
    )
    try:
        r = await http.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=90.0,
        )
        r.raise_for_status()
        extra = _sanitize_llm_line(r.json().get("response", ""))
        if not extra:
            return _dict_expand(query)
        return f"{query.strip()}\nRelated terms: {extra}"
    except Exception as e:
        logger.warning("Ollama query expansion failed, falling back to dict: %s", e)
        return _dict_expand(query)


async def expand_search_query(
    query: str,
    settings: Settings,
    http: httpx.AsyncClient | None,
) -> str:
    mode = settings.query_expansion_mode
    q = query.strip()
    if not q or mode == "none":
        return q
    if mode == "dict":
        return _dict_expand(q)
    if mode == "ollama":
        if http and settings.ollama_expand_model.strip():
            return await _ollama_expand(q, settings, http)
        return _dict_expand(q)
    return q
