from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, DbDep, VectorStoreDep
from app.schemas.recommend import RecommendResponse
from app.services.recommendation_service import recommend_for_user

router = APIRouter()


@router.get("/", response_model=RecommendResponse)
async def recommend(
    db: DbDep,
    vector_store: VectorStoreDep,
    current: CurrentUserDep,
    limit: int = Query(10, ge=1, le=100),
    min_score: float = Query(
        0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity to the interest vector",
    ),
) -> RecommendResponse:
    items = await recommend_for_user(
        db,
        vector_store,
        user_id=current.id,
        limit=limit,
        min_score=min_score,
    )
    return RecommendResponse(items=items)
