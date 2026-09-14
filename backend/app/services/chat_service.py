from typing import Optional, Sequence, Any

from fastapi import HTTPException, status

from app.core.authorization import is_admin_user
from app.model.chat import Chat
from app.model.user import User
from app.repository.chat_repository import ChatRepository
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatListResponse,
    ChatMessageResponse,
    ChatResponse,
    ChatAskRequest,
    ChatAskResponse,
    ChatCreate,
    ChatUpdate,
)


class ChatService:
    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

    async def get_chats(
        self,
        user: User,
        limit: int = 20,
        cursor: Optional[int] = None,
    ) -> ChatListResponse:
        owner_id = None if is_admin_user(user) else user.id

        # Lấy dư 1 phần tử (limit + 1) để xác định has_more
        raw_items = await self.chat_repo.get_paginated(
            owner_id=owner_id,
            limit=limit + 1,
            cursor=cursor,
        )

        has_more = len(raw_items) > limit
        items = list(raw_items[:limit])
        next_cursor = items[-1].id if has_more and items else None

        return ChatListResponse(
            items=[ChatResponse.model_validate(item) for item in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def get_chat(self, chat_id: int, current_user: User) -> Chat:
        chat = await self._get_owned_or_admin_chat(chat_id, current_user)
        return chat

    async def get_chat_history(
        self,
        chat_id: int,
        current_user: User,
        limit: int = 20,
        cursor: Optional[int] = None,
    ) -> ChatHistoryResponse:
        chat = await self._get_owned_or_admin_chat(chat_id, current_user)
        raw_messages = await self.chat_repo.get_messages_paginated(
            chat_id=chat.id,
            limit=limit + 1,
            cursor=cursor,
        )

        has_more = len(raw_messages) > limit
        messages = list(raw_messages[:limit])
        next_cursor = messages[-1].id if has_more and messages else None

        return ChatHistoryResponse(
            chat=ChatResponse.model_validate(chat),
            messages=[
                ChatMessageResponse.model_validate(message) for message in messages
            ],
            next_cursor=next_cursor,
            has_more=has_more,
        )

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

    async def ask_question(
        self, chat_id: int, question_in: ChatAskRequest, current_user: User
    ) -> ChatAskResponse:
        chat = await self._get_owned_or_admin_chat(chat_id, current_user)

        question = question_in.question.strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty",
            )

        result = await self._run_rag(question)
        citations = result.get("citations", []) or []

        return ChatAskResponse(
            chat_id=chat.id,
            question=question,
            answer=result.get(
                "answer",
            ),
            valid=bool(result.get("valid", False)),
            citations=[
                {
                    "source": citation.get("source"),
                    "pages": citation.get("pages", []),
                }
                for citation in citations
            ],
        )

    async def _run_rag(self, question: str) -> dict[str, Any]:
        try:
            from app.ai_agent.rag_pipeline import run_pipeline

            result = run_pipeline(question)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        return {
            "valid": False,
            "answer": "Tài liệu hiện tại không đề cập vấn đề này.",
            "citations": [],
        }

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