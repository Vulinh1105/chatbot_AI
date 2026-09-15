from typing import Sequence
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        """Fetch a single user by primary key ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a single user by email address."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        """Fetch a single user by username."""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalars().first()

    async def get_multi(
            self, skip: int = 0, limit: int = 100
    ) -> Sequence[User]:
        """Fetch a list of users with pagination."""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit).order_by(User.id)
        )
        return result.scalars().all()

    async def create(
            self, user_in: UserCreate, hashed_password: str
    ) -> User:
        """Create and commit a new user."""
        db_user = User(
            username=user_in.username,
            email=str(user_in.email),
            password_hash=hashed_password,
        )
        self.db.add(db_user)
        await self._commit()
        await self.db.refresh(db_user)
        return db_user

    async def update(
            self, db_user: User, user_in: UserUpdate
    ) -> User:
        """Update an existing user."""
        if user_in.username is not None:
            db_user.username = user_in.username
        if user_in.email is not None:
            db_user.email = str(user_in.email)
        await self._commit()
        await self.db.refresh(db_user)
        return db_user

    async def delete(self, db_user: User) -> None:
        """Delete a user from the database."""
        await self.db.delete(db_user)
        await self._commit()

    async def _commit(self) -> None:
        """Commit changes and leave the request session usable after a failure."""
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
