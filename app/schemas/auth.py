from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegister(BaseModel):
    """MVP: no strict EmailStr (avoids seed/local dev rejections); tighten in production."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def email_normalized(cls, v: str) -> str:
        e = v.strip().lower()
        if "@" not in e or "." not in e.split("@", 1)[-1]:
            raise ValueError("Invalid email format")
        return e


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
