from fastapi import APIRouter

from app.api.routes import auth, posts, recommend, search

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(recommend.router, prefix="/recommend", tags=["recommend"])
