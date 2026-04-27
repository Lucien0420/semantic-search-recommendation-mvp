from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep, SettingsDep
from app.models.user import User
from app.schemas.auth import Token, UserPublic, UserRegister
from app.services.jwt_tokens import create_access_token
from app.services.passwords import hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: DbDep) -> User:
    email = body.email
    stmt = select(User).where(User.email == email)
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(email=email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return user


@router.post("/token", response_model=Token)
async def login(
    db: DbDep,
    settings: SettingsDep,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    email = form.username.lower().strip()
    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    token = create_access_token(settings, user_id=user.id, email=user.email)
    await db.commit()
    return Token(access_token=token)


@router.get("/me", response_model=UserPublic)
async def read_me(current: CurrentUserDep) -> User:
    return current
