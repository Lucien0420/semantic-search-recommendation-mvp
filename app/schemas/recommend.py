from pydantic import BaseModel, Field

from app.schemas.post import PostReadWithScore


class RecommendQuery(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity to the interest vector",
    )


class RecommendResponse(BaseModel):
    items: list[PostReadWithScore]
