from datetime import datetime, timezone
from unittest import TestCase

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.model.chat import Chat
from app.model.chat_message import ChatMessage, ChatMessageRole, ChatMessageStatus
from app.model.user import User
from app.schemas.chat import ChatMessageResponse


class ChatMessageSchemaTests(TestCase):
    def test_response_serializes_rag_sources(self) -> None:
        response = ChatMessageResponse(
            id=2,
            chat_id=1,
            role=ChatMessageRole.SYSTEM,
            content="Nội dung trả lời",
            sources=[{"source": "policy.pdf", "pages": [2, 3]}],
            status=ChatMessageStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
        )

        payload = response.model_dump(mode="json")

        self.assertEqual(payload["role"], "system")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(
            payload["sources"],
            [{"source": "policy.pdf", "pages": [2, 3]}],
        )

    def test_source_preserves_extra_rag_metadata(self) -> None:
        response = ChatMessageResponse(
            id=2,
            chat_id=1,
            role="system",
            content="Nội dung trả lời",
            sources=[
                {
                    "source": "policy.pdf",
                    "pages": [2],
                    "chunk_id": "doc1_p2_c001",
                }
            ],
            status="completed",
            created_at=datetime.now(timezone.utc),
        )

        self.assertEqual(
            response.model_dump(mode="json")["sources"][0]["chunk_id"],
            "doc1_p2_c001",
        )


class ChatMessageModelTests(TestCase):
    def test_defaults_and_chat_delete_cascade(self) -> None:
        engine = create_engine("sqlite:///:memory:")

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
            del connection_record
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)

        with Session(engine) as session:
            user = User(
                username="tester",
                email="tester@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.flush()
            chat = Chat(owner_id=user.id, title="Test chat")
            message = ChatMessage(
                chat=chat,
                role=ChatMessageRole.SYSTEM,
                content="",
            )
            session.add(message)
            session.commit()

            self.assertEqual(message.status, ChatMessageStatus.PENDING)
            self.assertEqual(message.sources, [])

            session.delete(chat)
            session.commit()

            message_count = session.scalar(
                select(func.count()).select_from(ChatMessage)
            )
            self.assertEqual(message_count, 0)

        engine.dispose()
