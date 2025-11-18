from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.schemas.user import (
    RequestUserModel,
    RequestUserUpdateModel,
    ResponseUserModel,
    UserModel,
)
from src.services.user_service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=Optional[list[ResponseUserModel]] | None,
    status_code=status.HTTP_200_OK,
)
async def get_users(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    user_status: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[ResponseUserModel]:
    return await UserService(session).get_users(
        user_id=user_id,
        email=email,
        user_status=user_status,
    )


@router.post("", status_code=status.HTTP_200_OK)
async def post_user(
    user: RequestUserModel, session: AsyncSession = Depends(get_async_session)
) -> UserModel:
    return await UserService(session).create_user(user)


@router.patch("/{user_id}", response_model=Optional[UserModel])
async def patch_user(
    user_id: int,
    user: RequestUserUpdateModel,
    session: AsyncSession = Depends(get_async_session),
) -> UserModel:
    return await UserService(session).update_user_status(user_id, user)
