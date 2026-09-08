from typing import Sequence

from fastapi import HTTPException, status

from app.core.authorization import is_admin_user
from app.model.chat import Chat
from app.model.user import User
from app.repository.chat_repository import ChatRepository
from app.schemas.chat import ChatCreate, ChatUpdate


class ChatService:
    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

    async def get_chats(self, current_user: User) -> Sequence[Chat]:
        if is_admin_user(current_user):
            return await self.chat_repo.get_all()
        return await self.chat_repo.get_by_owner(current_user.id)

    async def get_chat(self, chat_id: int, current_user: User) -> Chat:
        chat = await self._get_owned_or_admin_chat(chat_id, current_user)
        return chat

    async def create_chat(self, chat_in: ChatCreate, current_user: User) -> Chat:
        return await self.chat_repo.create(owner_id=current_user.id, chat_in=chat_in)

    async def update_chat(
        self, chat_id: int, chat_in: ChatUpdate, current_user: User
    ) -> Chat:
        chat = await self._get_owned_or_admin_chat(chat_id, current_user)
        return await self.chat_repo.update(chat=chat, chat_in=chat_in)

    async def delete_chat(self, chat_id: int, current_user: User) -> None:
        chat = await self._get_owned_or_admin_chat(chat_id, current_user)
        await self.chat_repo.delete(chat)

    async def _get_owned_or_admin_chat(self, chat_id: int, current_user: User) -> Chat:
        chat = await self.chat_repo.get_by_id(chat_id)
        if chat is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )
        if chat.owner_id != current_user.id and not is_admin_user(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this chat",
            )
        return chat
