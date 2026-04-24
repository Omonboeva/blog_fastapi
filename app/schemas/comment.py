from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.user import UserPublicResponse


class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentCreate(CommentBase):
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentResponse(CommentBase):
    id: int
    post_id: int
    parent_id: Optional[int]
    author_id: int
    author: UserPublicResponse
    likes_count: int
    is_approved: bool
    replies: List["CommentResponse"] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


CommentResponse.model_rebuild()


class PaginatedCommentsResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int