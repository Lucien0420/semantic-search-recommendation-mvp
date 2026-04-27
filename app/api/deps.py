from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.user import User
from app.services.embedding_service import EmbeddingService
from app.services.jwt_tokens import decode_access_token
from app.services.vector_db import VectorStore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

DbDep = Annotated[AsyncSession, Depends(get_db)]


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_embedding_service(
    settings: Annotated[Settings, Depends(get_settings)],
    http: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> EmbeddingService:
    return EmbeddingService(settings, http)


VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbDep,
    settings: SettingsDep,
) -> User:
    bad = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(settings, token)
        uid = int(payload["sub"])
    except Exception:
        raise bad
    user = await db.get(User, uid)
    if user is None or not user.is_active:
        raise bad
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
