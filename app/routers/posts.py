from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.crud import post as post_crud
from app.models.post import PostStatus
from app.models.user import User
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    PaginatedPostsResponse,
)

router = APIRouter(prefix="/posts", tags=["📝 Posts"])


@router.get(
    "/",
    response_model=PaginatedPostsResponse,
    summary="Postlar ro'yxati",
)
async def get_posts(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    page_size: int = Query(10, ge=1, le=50, description="Har sahifadagi postlar soni"),
    search: Optional[str] = Query(None, description="Qidiruv so'zi"),
    author_id: Optional[int] = Query(None, description="Muallif ID"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPostsResponse:
    """
    Chop etilgan postlarni ko'rish.
    Anonim foydalanuvchilar faqat `published` postlarni ko'ra oladi.
    """
    skip = (page - 1) * page_size
    posts, total = await post_crud.get_posts(
        db,
        skip=skip,
        limit=page_size,
        status=PostStatus.PUBLISHED,
        author_id=author_id,
        search=search,
    )

    total_pages = (total + page_size - 1) // page_size
    return PaginatedPostsResponse(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/my",
    response_model=PaginatedPostsResponse,
    summary="Mening postlarim",
)
async def get_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[PostStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPostsResponse:
    """Joriy foydalanuvchining barcha postlari (draft, published, archived)."""
    skip = (page - 1) * page_size
    posts, total = await post_crud.get_posts(
        db,
        skip=skip,
        limit=page_size,
        status=status,
        author_id=current_user.id,
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedPostsResponse(
        items=posts, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi post yaratish",
)
async def create_post(
    post_in: PostCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostResponse:
    """
    Yangi blog post yaratish.
    - **title**: Post sarlavhasi
    - **content**: Post matni (Markdown qo'llab-quvvatlanadi)
    - **status**: `draft` | `published` | `archived`
    """
    post = await post_crud.create_post(db, post_in, author_id=current_user.id)
    return post


@router.get(
    "/{slug}",
    response_model=PostResponse,
    summary="Postni ko'rish",
)
async def get_post_by_slug(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostResponse:
    """Slug bo'yicha postni olish va ko'rishlar sonini oshirish."""
    post = await post_crud.get_post_by_slug(db, slug)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post topilmadi",
        )

    if post.status != PostStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu post hali nashr etilmagan",
        )

    # Ko'rishlar sonini oshirish (background'da)
    await post_crud.increment_views(db, post.id)
    return post


@router.get(
    "/id/{post_id}",
    response_model=PostResponse,
    summary="Postni ID bo'yicha ko'rish",
)
async def get_post_by_id(
    post_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostResponse:
    """ID bo'yicha postni olish (o'z postlari uchun)."""
    post = await post_crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post topilmadi")

    # Faqat o'z postini yoki admin ko'ra oladi
    if post.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    return post


@router.put(
    "/{post_id}",
    response_model=PostResponse,
    summary="Postni yangilash",
)
async def update_post(
    post_id: int,
    post_in: PostUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostResponse:
    """Postni yangilash (faqat muallif yoki admin)."""
    post = await post_crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post topilmadi")

    if post.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu postni tahrirlash uchun ruxsat yo'q",
        )

    updated_post = await post_crud.update_post(db, post, post_in)
    return updated_post


@router.post(
    "/{post_id}/like",
    summary="Postni layk qilish",
)
async def like_post(
    post_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Postga like berish."""
    post = await post_crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post topilmadi")

    new_count = await post_crud.increment_likes(db, post_id)
    return {"likes_count": new_count}


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Postni o'chirish",
)
async def delete_post(
    post_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Postni o'chirish (faqat muallif yoki admin)."""
    post = await post_crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post topilmadi")

    if post.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu postni o'chirish uchun ruxsat yo'q",
        )

    await post_crud.delete_post(db, post)


# ─── Admin endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/admin/all",
    response_model=PaginatedPostsResponse,
    summary="[Admin] Barcha postlar",
)
async def admin_get_all_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[PostStatus] = None,
    author_id: Optional[int] = None,
    search: Optional[str] = None,
    _: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPostsResponse:
    """[Admin] Barcha postlarni (draft, published, archived) ko'rish."""
    skip = (page - 1) * page_size
    posts, total = await post_crud.get_posts(
        db, skip=skip, limit=page_size, status=status, author_id=author_id, search=search
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedPostsResponse(
        items=posts, total=total, page=page, page_size=page_size, total_pages=total_pages
    )