from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.user_action import UserAction

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tags: Mapped[list[Any]] = mapped_column(JSON, nullable=False, insert_default=list)
    content_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="text",
        doc="MVP: text; reserved for image / video, etc.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    actions: Mapped[list["UserAction"]] = relationship(
        "UserAction",
        back_populates="post",
        cascade="all, delete-orphan",
    )
