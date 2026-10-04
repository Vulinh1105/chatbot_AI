from unittest.mock import AsyncMock

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.model.chat import Chat
from app.model.chat_message import ChatMessage, ChatMessageRole
from app.model.user import User
from app.repository.chat_repository import ChatRepository
from app.schemas.chat import ChatAskRequest
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_ask_question_persists_question_and_answer() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        del connection_record
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        user = User(
            username="tester",
            email="tester@example.com",
            password_hash="hash",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        chat = Chat(owner_id=user.id, title="Test chat")
        session.add(chat)
        await session.commit()
        await session.refresh(chat)

        repo = ChatRepository(session)
        service = ChatService(repo)
        service._run_rag = AsyncMock(
            return_value={
                "valid": True,
                "answer": "Đây là câu trả lời",
                "citations": [{"source": "policy.pdf", "pages": [2, 3]}],
            }
        )

        response = await service.ask_question(
            chat_id=chat.id,
            question_in=ChatAskRequest(question="Câu hỏi mẫu"),
            current_user=user,
        )

        assert response.chat_id == chat.id
        assert response.role == ChatMessageRole.SYSTEM
        assert response.content == "Đây là câu trả lời"
        assert response.sources[0].source == "policy.pdf"
        assert response.sources[0].pages == [2, 3]

        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat.id)
            .order_by(ChatMessage.id.asc())
        )
        messages = result.scalars().all()

        assert len(messages) == 2
        assert messages[0].role == ChatMessageRole.USER
        assert messages[0].content == "Câu hỏi mẫu"
        assert messages[1].role == ChatMessageRole.SYSTEM
        assert messages[1].content == "Đây là câu trả lời"
        assert messages[1].sources == [
            {"source": "policy.pdf", "pages": [2, 3]}
        ]

    await engine.dispose()
