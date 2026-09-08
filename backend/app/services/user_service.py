from typing import Sequence

from fastapi import HTTPException, status

from app.core.security import hash_password
from app.model.user import User
from app.repository.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Business logic for authenticated-user and administrator user operations."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_current_user(self, current_user: User) -> User:
        return current_user

    async def update_current_user(self, current_user: User, user_in: UserUpdate) -> User:
        await self._ensure_unique_values(user_in, exclude_user_id=current_user.id)
        return await self.user_repo.update(db_user=current_user, user_in=user_in)

    async def delete_current_user(self, current_user: User) -> None:
        await self.user_repo.delete(db_user=current_user)

    async def get_users(self, skip: int = 0, limit: int = 100) -> Sequence[User]:
        return await self.user_repo.get_multi(skip=skip, limit=limit)

    async def create_user(self, user_in: UserCreate) -> User:
        await self._ensure_unique_values(user_in)
        return await self.user_repo.create(
            user_in=user_in,
            hashed_password=hash_password(user_in.password),
        )

    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.user_repo.get_by_id(user_id=user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def update_user(self, user_id: int, user_in: UserUpdate) -> User:
        user = await self.get_user_by_id(user_id)
        await self._ensure_unique_values(user_in, exclude_user_id=user.id)
        return await self.user_repo.update(db_user=user, user_in=user_in)

    async def delete_user(self, user_id: int) -> None:
        user = await self.get_user_by_id(user_id)
        await self.user_repo.delete(db_user=user)

    async def _ensure_unique_values(
        self,
        user_in: UserCreate | UserUpdate,
        *,
        exclude_user_id: int | None = None,
    ) -> None:
        if user_in.username is not None:
            existing_user = await self.user_repo.get_by_username(user_in.username)
            if existing_user and existing_user.id != exclude_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this username already exists.",
                )

        if user_in.email is not None:
            existing_user = await self.user_repo.get_by_email(str(user_in.email))
            if existing_user and existing_user.id != exclude_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email already exists.",
                )
