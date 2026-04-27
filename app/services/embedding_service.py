from __future__ import annotations

import logging
import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Text embeddings via Ollama or OpenAI; replaceable with a multimodal pipeline later."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http_client

    async def embed(self, text: str) -> list[float]:
        if self._settings.embedding_backend == "openai":
            return await self._embed_openai(text)
        return await self._embed_ollama(text)

    async def _embed_ollama(self, text: str) -> list[float]:
        payload = {
            "model": self._settings.ollama_embed_model,
            "prompt": text,
        }
        try:
            r = await self._http.post(
                self._settings.ollama_embeddings_url,
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            emb = data.get("embedding")
            if not isinstance(emb, list) or not emb:
                raise ValueError("Ollama response missing embedding")
            return [float(x) for x in emb]
        except Exception as e:
            logger.exception("Ollama embedding failed: %s", e)
            raise

    async def _embed_openai(self, text: str) -> list[float]:
        key = self._settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY is not set")
        url = "https://api.openai.com/v1/embeddings"
        payload = {
            "model": self._settings.openai_embed_model,
            "input": text,
        }
        headers = {"Authorization": f"Bearer {key}"}
        try:
            r = await self._http.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            emb = data["data"][0]["embedding"]
            return [float(x) for x in emb]
        except Exception as e:
            logger.exception("OpenAI embedding failed: %s", e)
            raise
