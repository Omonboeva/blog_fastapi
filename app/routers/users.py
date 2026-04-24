from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserPublicResponse,
    UserUpdate,
    UserPasswordUpdate,
)

router = APIRouter(prefix="/users", tags=["👤 Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Mening profilim",
)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Profilni yangilash",
)
async def update_my_profile(
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:

    updated_user = await user_crud.update_user(db, current_user, user_in)
    return updated_user


@router.put(
    "/me/password",
    summary="Parolni o'zgartirish",
)
async def change_my_password(
    password_data: UserPasswordUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    success, message = await user_crud.change_password(
        db, current_user, password_data.old_password, password_data.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return {"message": message}


@router.get(
    "/{username}",
    response_model=UserPublicResponse,
    summary="Foydalanuvchi profili",
)
async def get_user_profile(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPublicResponse:

    user = await user_crud.get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi",
        )
    return user


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="[Admin] Barcha foydalanuvchilar",
)
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    _: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[UserResponse]:

    users, _ = await user_crud.get_users(db, skip=skip, limit=limit, is_active=is_active)
    return users


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Foydalanuvchini o'chirish",
)
async def delete_user(
    user_id: int,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:

    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O'zingizni o'chira olmaysiz",
        )

    user = await user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi")

    await user_crud.delete_user(db, user)


@router.patch(
    "/{user_id}/deactivate",
    summary="[Admin] Foydalanuvchini bloklash",
)
async def deactivate_user(
    user_id: int,
    _: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:

    success = await user_crud.deactivate_user(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi")
    return {"message": "Foydalanuvchi bloklandi"}