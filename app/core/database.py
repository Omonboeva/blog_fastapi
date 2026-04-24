from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Asinxron engine yaratish
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,          # SQL loglarini ko'rsatish (development uchun)
    pool_size=10,       # Ulanishlar soni
    max_overflow=20,    # Qo'shimcha ulanishlar
    pool_pre_ping=True, # Ulanishni tekshirish
)

# Asinxron session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Barcha modellar uchun asosiy klass."""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency injection uchun DB session.
    Har bir request uchun yangi session ochiladi va
    request tugagandan keyin yopiladi.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()