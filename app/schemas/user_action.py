from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LikeCreate(BaseModel):
    user_id: int = Field(..., ge=1)


class LikeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    post_id: int
    action_type: str
    created_at: datetime
