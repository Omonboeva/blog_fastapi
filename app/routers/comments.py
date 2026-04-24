from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.crud import comment as comment_crud
from app.crud import post as post_crud
from app.models.user import User
from app.schemas.comment import (
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    PaginatedCommentsResponse,
)

router = APIRouter(tags=["💬 Comments"])



@router.get(
    "/posts/{post_id}/comments",
    response_model=PaginatedCommentsResponse,
    summary="Post commentlari",
)
async def get_post_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCommentsResponse:

    post = await post_crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post topilmadi")

    skip = (page - 1) * page_size
    comments, total = await comment_crud.get_post_comments(
        db, post_id=post_id, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedCommentsResponse(
        items=comments, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Comment qo'shish",
)
async def create_comment(
    post_id: int,
    comment_in: CommentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:
    post = await post_crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post topilmadi")


    if comment_in.parent_id:
        parent = await comment_crud.get_comment(db, comment_in.parent_id)
        if not parent or parent.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Noto'g'ri parent comment",
            )

    comment = await comment_crud.create_comment(
        db, comment_in, post_id=post_id, author_id=current_user.id
    )
    return comment



@router.get(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Commentni ko'rish",
)
async def get_comment(
    comment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:

    comment = await comment_crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment topilmadi")
    return comment


@router.put(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Commentni tahrirlash",
)
async def update_comment(
    comment_id: int,
    comment_in: CommentUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:

    comment = await comment_crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment topilmadi")

    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu commentni tahrirlash uchun ruxsat yo'q",
        )

    updated_comment = await comment_crud.update_comment(db, comment, comment_in)
    return updated_comment


@router.post(
    "/comments/{comment_id}/like",
    summary="Commentni layk qilish",
)
async def like_comment(
    comment_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:

    comment = await comment_crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment topilmadi")

    new_count = await comment_crud.like_comment(db, comment_id)
    return {"likes_count": new_count}


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Commentni o'chirish",
)
async def delete_comment(
    comment_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:

    comment = await comment_crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment topilmadi")

    if comment.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu commentni o'chirish uchun ruxsat yo'q",
        )

    await comment_crud.delete_comment(db, comment)



@router.patch(
    "/comments/{comment_id}/approve",
    summary="[Admin] Commentni tasdiqlash",
)
async def approve_comment(
    comment_id: int,
    _: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:

    success = await comment_crud.approve_comment(db, comment_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment topilmadi")
    return {"message": "Comment tasdiqlandi"}


@router.get(
    "/users/{user_id}/comments",
    response_model=PaginatedCommentsResponse,
    summary="Foydalanuvchi commentlari",
)
async def get_user_comments(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCommentsResponse:

    skip = (page - 1) * page_size
    comments, total = await comment_crud.get_user_comments(
        db, user_id=user_id, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedCommentsResponse(
        items=comments, total=total, page=page, page_size=page_size, total_pages=total_pages
    )