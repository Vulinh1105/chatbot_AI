from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.model.chat_message import ChatMessageRole, ChatMessageStatus


class ChatCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str
    pages: list[int] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    role: ChatMessageRole
    content: str
    sources: list[ChatMessageSource] = Field(default_factory=list)
    status: ChatMessageStatus
    created_at: datetime
