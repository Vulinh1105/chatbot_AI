from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_current_admin_user,
    get_current_user,
    get_user_service,
)
from app.model.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return await user_service.get_current_user(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current authenticated user profile",
)
async def update_current_user_profile(
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return await user_service.update_current_user(current_user, user_in)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current authenticated user account",
)
async def delete_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await user_service.delete_current_user(current_user)


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="[Admin] List all users with pagination",
)
async def read_users(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> Sequence[User]:
    return await user_service.get_users(skip=skip, limit=limit)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a new user",
)
async def create_user_by_admin(
    user_in: UserCreate,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return await user_service.create_user(user_in)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="[Admin] Get a user by ID",
)
async def read_user_by_id(
    user_id: int,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return await user_service.get_user_by_id(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="[Admin] Update any user by ID",
)
async def update_user_by_id(
    user_id: int,
    user_in: UserUpdate,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return await user_service.update_user(user_id, user_in)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Delete any user by ID",
)
async def delete_user_by_id(
    user_id: int,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await user_service.delete_user(user_id)
