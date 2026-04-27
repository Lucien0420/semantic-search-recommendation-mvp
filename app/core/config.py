from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db",
        alias="DATABASE_URL",
    )
    chroma_path: str = Field(default="./chroma_db", alias="CHROMA_PATH")
    chroma_collection: str = Field(default="posts", alias="CHROMA_COLLECTION")

    embedding_backend: Literal["ollama", "openai"] = Field(
        default="ollama",
        alias="EMBEDDING_BACKEND",
    )
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        alias="OLLAMA_BASE_URL",
    )
    ollama_embed_model: str = Field(
        default="nomic-embed-text",
        alias="OLLAMA_EMBED_MODEL",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_embed_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBED_MODEL",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-only-change-me-32bytes-minimum!!"),
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    query_expansion_mode: Literal["none", "dict", "ollama"] = Field(
        default="dict",
        alias="QUERY_EXPANSION_MODE",
    )
    ollama_expand_model: str = Field(
        default="",
        alias="OLLAMA_EXPAND_MODEL",
        description="If set and mode=ollama, use Ollama /api/generate to expand the query",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ollama_embeddings_url(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}/api/embeddings"


@lru_cache
def get_settings() -> Settings:
    return Settings()
