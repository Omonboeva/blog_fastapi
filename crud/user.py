from typing import Optional, List

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """ID bo'yicha foydalanuvchini olish."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Email bo'yicha foydalanuvchini olish."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Username bo'yicha foydalanuvchini olish."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None,
) -> tuple[List[User], int]:
    """Barcha foydalanuvchilarni olish (pagination bilan)."""
    query = select(User)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Jami soni
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Ma'lumotlar
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return list(users), total


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """Yangi foydalanuvchi yaratish."""
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        bio=user_in.bio,
        avatar_url=user_in.avatar_url,
    )
    db.add(db_user)
    await db.flush()   # ID generatsiya qilish uchun
    await db.refresh(db_user)
    return db_user


async def update_user(
    db: AsyncSession, db_user: User, user_in: UserUpdate
) -> User:
    """Foydalanuvchi ma'lumotlarini yangilash."""
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def change_password(
    db: AsyncSession, db_user: User, old_password: str, new_password: str
) -> tuple[bool, str]:
    """Parolni o'zgartirish."""
    if not verify_password(old_password, db_user.hashed_password):
        return False, "Eski parol noto'g'ri"

    db_user.hashed_password = get_password_hash(new_password)
    db.add(db_user)
    await db.flush()
    return True, "Parol muvaffaqiyatli o'zgartirildi"


async def authenticate_user(
    db: AsyncSession, username_or_email: str, password: str
) -> Optional[User]:
    """Foydalanuvchini autentifikatsiya qilish."""
    # Email yoki username bo'yicha qidirish
    if "@" in username_or_email:
        user = await get_user_by_email(db, username_or_email)
    else:
        user = await get_user_by_username(db, username_or_email)

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def deactivate_user(db: AsyncSession, user_id: int) -> bool:
    """Foydalanuvchini bloklash."""
    result = await db.execute(
        update(User).where(User.id == user_id).values(is_active=False)
    )
    return result.rowcount > 0


async def delete_user(db: AsyncSession, db_user: User) -> None:
    """Foydalanuvchini o'chirish (cascade: postlar va commentlar ham o'chadi)."""
    await db.delete(db_user)
    await db.flush()