from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import Settings


def create_access_token(settings: Settings, *, user_id: int, email: str) -> str:
    secret = settings.jwt_secret_key.get_secret_value()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    secret = settings.jwt_secret_key.get_secret_value()
    return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
