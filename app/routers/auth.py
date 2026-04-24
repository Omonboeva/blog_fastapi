from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.crud import user as user_crud
from app.schemas.user import UserCreate, UserResponse, TokenResponse, RefreshTokenRequest

router = APIRouter(prefix="/auth", tags=["🔐 Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ro'yxatdan o'tish",
)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Yangi foydalanuvchi ro'yxatdan o'tkazish.
    - **username**: 3-50 ta belgi, faqat harf/raqam/_
    - **email**: To'g'ri email manzil
    - **password**: Kamida 8 ta belgi
    """
    # Email mavjudligini tekshirish
    existing_email = await user_crud.get_user_by_email(db, user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email allaqachon ro'yxatdan o'tgan",
        )

    # Username mavjudligini tekshirish
    existing_username = await user_crud.get_user_by_username(db, user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu username band",
        )

    user = await user_crud.create_user(db, user_in)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Tizimga kirish",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    JWT token olish uchun login.
    - **username**: Username yoki email
    - **password**: Parol
    """
    user = await user_crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/email yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi bloklangan",
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Token yangilash",
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Refresh token orqali yangi access token olish."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token noto'g'ri yoki muddati o'tgan",
    )

    payload = decode_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = await user_crud.get_user(db, int(user_id))
    if not user or not user.is_active:
        raise credentials_exception

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )