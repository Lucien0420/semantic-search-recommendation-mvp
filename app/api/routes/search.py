from fastapi import APIRouter, Query

from app.api.deps import DbDep, EmbeddingServiceDep, HttpClientDep, SettingsDep, VectorStoreDep
from app.schemas.search import SearchResponse
from app.services.search_service import semantic_search

router = APIRouter()


@router.get("/", response_model=SearchResponse)
async def search_posts(
    db: DbDep,
    vector_store: VectorStoreDep,
    embedding_service: EmbeddingServiceDep,
    settings: SettingsDep,
    http: HttpClientDep,
    q: str = Query(..., min_length=1, max_length=2000),
    limit: int = Query(10, ge=1, le=100),
    min_score: float = Query(
        0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity (1 - Chroma cosine distance)",
    ),
) -> SearchResponse:
    items = await semantic_search(
        db,
        vector_store,
        embedding_service,
        settings,
        http,
        query=q,
        limit=limit,
        min_score=min_score,
    )
    return SearchResponse(items=items)
