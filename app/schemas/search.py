from pydantic import BaseModel, Field

from app.schemas.post import PostReadWithScore


class SearchQuery(BaseModel):
    q: str = Field(..., min_length=1, max_length=2000, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity; results below this are dropped",
    )


class SearchResponse(BaseModel):
    items: list[PostReadWithScore]
