import re
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.post import Post, PostStatus
from app.schemas.post import PostCreate, PostUpdate


def _generate_slug(title: str, post_id: Optional[int] = None) -> str:
    slug = title.lower().strip()
    replacements = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    for cyr, lat in replacements.items():
        slug = slug.replace(cyr, lat)

    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')

    if post_id:
        slug = f"{slug}-{post_id}"
    return slug[:350]


async def _ensure_unique_slug(db: AsyncSession, slug: str, exclude_id: Optional[int] = None) -> str:

    query = select(Post).where(Post.slug == slug)
    if exclude_id:
        query = query.where(Post.id != exclude_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        counter = 1
        while True:
            new_slug = f"{slug}-{counter}"
            result = await db.execute(
                select(Post).where(Post.slug == new_slug)
            )
            if not result.scalar_one_or_none():
                return new_slug
            counter += 1
    return slug


async def get_post(db: AsyncSession, post_id: int) -> Optional[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .where(Post.id == post_id)
    )
    return result.scalar_one_or_none()


async def get_post_by_slug(db: AsyncSession, slug: str) -> Optional[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .where(Post.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_posts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    status: Optional[PostStatus] = None,
    author_id: Optional[int] = None,
    search: Optional[str] = None,
) -> tuple[List[Post], int]:
    query = select(Post).options(selectinload(Post.author))

    if status:
        query = query.where(Post.status == status)
    if author_id:
        query = query.where(Post.author_id == author_id)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Post.title.ilike(search_term),
                Post.content.ilike(search_term),
                Post.excerpt.ilike(search_term),
            )
        )


    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Post.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()

    return list(posts), total


async def create_post(
    db: AsyncSession, post_in: PostCreate, author_id: int
) -> Post:
    base_slug = _generate_slug(post_in.title)
    slug = await _ensure_unique_slug(db, base_slug)

    published_at = None
    if post_in.status == PostStatus.PUBLISHED:
        published_at = datetime.now(timezone.utc)

    db_post = Post(
        title=post_in.title,
        slug=slug,
        content=post_in.content,
        excerpt=post_in.excerpt,
        cover_image_url=post_in.cover_image_url,
        status=post_in.status,
        author_id=author_id,
        published_at=published_at,
    )
    db.add(db_post)
    await db.flush()
    await db.refresh(db_post)
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .where(Post.id == db_post.id)
    )
    return result.scalar_one()


async def update_post(
    db: AsyncSession, db_post: Post, post_in: PostUpdate
) -> Post:
    update_data = post_in.model_dump(exclude_unset=True)

    if "title" in update_data:
        base_slug = _generate_slug(update_data["title"])
        update_data["slug"] = await _ensure_unique_slug(db, base_slug, exclude_id=db_post.id)

    if "status" in update_data:
        if update_data["status"] == PostStatus.PUBLISHED and db_post.status != PostStatus.PUBLISHED:
            update_data["published_at"] = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(db_post, field, value)

    db.add(db_post)
    await db.flush()

    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .where(Post.id == db_post.id)
    )
    return result.scalar_one()


async def increment_views(db: AsyncSession, post_id: int) -> None:

    await db.execute(
        update(Post)
        .where(Post.id == post_id)
        .values(views_count=Post.views_count + 1)
    )


async def increment_likes(db: AsyncSession, post_id: int) -> int:
    await db.execute(
        update(Post)
        .where(Post.id == post_id)
        .values(likes_count=Post.likes_count + 1)
    )
    result = await db.execute(select(Post.likes_count).where(Post.id == post_id))
    return result.scalar_one()


async def delete_post(db: AsyncSession, db_post: Post) -> None:
    await db.delete(db_post)
    await db.flush()