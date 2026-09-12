from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.chat import Chat
from app.schemas.chat import ChatCreate, ChatUpdate


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, chat_id: int) -> Chat | None:
        result = await self.db.execute(select(Chat).where(Chat.id == chat_id))
        return result.scalars().first()

    async def get_by_owner(self, owner_id: int) -> Sequence[Chat]:
        result = await self.db.execute(
            select(Chat)
            .where(Chat.owner_id == owner_id)
            .order_by(Chat.updated_at.desc(), Chat.id.desc())
        )
        return result.scalars().all()

    async def get_all(self) -> Sequence[Chat]:
        result = await self.db.execute(
            select(Chat).order_by(Chat.updated_at.desc(), Chat.id.desc())
        )
        return result.scalars().all()

    async def create(self, owner_id: int, chat_in: ChatCreate) -> Chat:
        chat = Chat(owner_id=owner_id, title=chat_in.title)
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def update(self, chat: Chat, chat_in: ChatUpdate) -> Chat:
        chat.title = chat_in.title
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def delete(self, chat: Chat) -> None:
        await self.db.delete(chat)
        await self.db.commit()
    async def get_paginated(
        self,
        owner_id: int | None = None,
        limit: int = 20,
        cursor: int | None = None,
    ) -> Sequence[Chat]:
        stmt = select(Chat)

        if owner_id is not None:
            stmt = stmt.where(Chat.owner_id == owner_id)

        if cursor is not None:
            stmt = stmt.where(Chat.id < cursor)

        stmt = stmt.order_by(Chat.updated_at.desc(), Chat.id.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()
