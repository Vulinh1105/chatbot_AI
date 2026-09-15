from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.model.chat import Chat
from app.model.chat_message import ChatMessage, ChatMessageRole
from app.model.user import User
from app.repository.chat_repository import ChatRepository
from app.schemas.chat import ChatAskRequest
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_ask_question_persists_question_and_answer() -> None:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        del connection_record
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    async def run_test() -> None:
        with SessionLocal() as session:
            user = User(
                username="tester",
                email="tester@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            chat = Chat(owner_id=user.id, title="Test chat")
            session.add(chat)
            session.commit()
            session.refresh(chat)

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

            assert response.question == "Câu hỏi mẫu"
            assert response.answer == "Đây là câu trả lời"

            messages = session.execute(
                select(ChatMessage)
                .where(ChatMessage.chat_id == chat.id)
                .order_by(ChatMessage.id.asc())
            ).scalars().all()

            assert len(messages) == 2
            assert messages[0].role == ChatMessageRole.USER
            assert messages[0].content == "Câu hỏi mẫu"
            assert messages[1].role == ChatMessageRole.SYSTEM
            assert messages[1].content == "Đây là câu trả lời"
            assert messages[1].sources == [{"source": "policy.pdf", "pages": [2, 3]}]

    await run_test()
    engine.dispose()
