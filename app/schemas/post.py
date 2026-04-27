from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=50_000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    content_type: str = Field(default="text", max_length=32)


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    author_id: int
    tags: list[str]
    content_type: str
    created_at: datetime


class PostReadWithScore(PostRead):
    similarity: float = Field(
        ..., ge=0.0, le=1.0, description="Cosine similarity to the query vector"
    )
