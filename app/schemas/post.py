
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.post import PostStatus
from app.schemas.user import UserPublicResponse



class PostBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    content: str = Field(..., min_length=10)
    excerpt: Optional[str] = Field(None, max_length=500)
    cover_image_url: Optional[str] = None


class PostCreate(PostBase):
    status: PostStatus = PostStatus.DRAFT

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    content: Optional[str] = Field(None, min_length=10)
    excerpt: Optional[str] = Field(None, max_length=500)
    cover_image_url: Optional[str] = None
    status: Optional[PostStatus] = None


class PostResponse(PostBase):
    id: int
    slug: str
    status: PostStatus
    views_count: int
    likes_count: int
    author_id: int
    author: UserPublicResponse
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str]
    cover_image_url: Optional[str]
    status: PostStatus
    views_count: int
    likes_count: int
    author: UserPublicResponse
    created_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PaginatedPostsResponse(BaseModel):
    items: list[PostListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int