from typing import Optional, List

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentUpdate


async def get_comment(db: AsyncSession, comment_id: int) -> Optional[Comment]:
    result = await db.execute(
        select(Comment)
        .options(
            selectinload(Comment.author),
            selectinload(Comment.replies).selectinload(Comment.author),
        )
        .where(Comment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def get_post_comments(
    db: AsyncSession,
    post_id: int,
    skip: int = 0,
    limit: int = 20,
    only_approved: bool = True,
) -> tuple[List[Comment], int]:

    query = (
        select(Comment)
        .options(
            selectinload(Comment.author),
            selectinload(Comment.replies).selectinload(Comment.author),
        )
        .where(Comment.post_id == post_id)
        .where(Comment.parent_id.is_(None))
    )

    if only_approved:
        query = query.where(Comment.is_approved == True)


    count_query = select(func.count()).select_from(
        select(Comment)
        .where(Comment.post_id == post_id)
        .where(Comment.parent_id.is_(None))
        .subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Comment.created_at.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    comments = result.scalars().all()

    return list(comments), total


async def get_user_comments(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
) -> tuple[List[Comment], int]:
    query = (
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.author_id == user_id)
    )

    count_query = select(func.count()).select_from(
        select(Comment).where(Comment.author_id == user_id).subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Comment.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    comments = result.scalars().all()

    return list(comments), total


async def create_comment(
    db: AsyncSession,
    comment_in: CommentCreate,
    post_id: int,
    author_id: int,
) -> Comment:

    db_comment = Comment(
        content=comment_in.content,
        post_id=post_id,
        author_id=author_id,
        parent_id=comment_in.parent_id,
    )
    db.add(db_comment)
    await db.flush()

    result = await db.execute(
        select(Comment)
        .options(
            selectinload(Comment.author),
            selectinload(Comment.replies),
        )
        .where(Comment.id == db_comment.id)
    )
    return result.scalar_one()


async def update_comment(
    db: AsyncSession, db_comment: Comment, comment_in: CommentUpdate
) -> Comment:
    db_comment.content = comment_in.content
    db.add(db_comment)
    await db.flush()

    result = await db.execute(
        select(Comment)
        .options(
            selectinload(Comment.author),
            selectinload(Comment.replies).selectinload(Comment.author),
        )
        .where(Comment.id == db_comment.id)
    )
    return result.scalar_one()


async def approve_comment(db: AsyncSession, comment_id: int) -> bool:
    result = await db.execute(
        update(Comment)
        .where(Comment.id == comment_id)
        .values(is_approved=True)
    )
    return result.rowcount > 0


async def like_comment(db: AsyncSession, comment_id: int) -> int:
    await db.execute(
        update(Comment)
        .where(Comment.id == comment_id)
        .values(likes_count=Comment.likes_count + 1)
    )
    result = await db.execute(
        select(Comment.likes_count).where(Comment.id == comment_id)
    )
    return result.scalar_one()


async def delete_comment(db: AsyncSession, db_comment: Comment) -> None:
    await db.delete(db_comment)
    await db.flush()