from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_chat_service, get_current_user
from app.model.chat import Chat
from app.model.user import User
from app.schemas.chat import ChatCreate, ChatListResponse, ChatResponse, ChatUpdate
from app.services.chat_service import ChatService

router = APIRouter()


@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a chat",
)
async def create_chat(
    chat_in: ChatCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> Chat:
    return await chat_service.create_chat(chat_in, current_user)


@router.get(
    "/",
    response_model=ChatListResponse,
    summary="List chats available to the current user with pagination",
)
async def read_chats(
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    limit: int = Query(20, ge=1, le=100, description="Số lượng chat cần lấy"),
    cursor: Optional[int] = Query(None, description="Cursor là id của chat cuối cùng ở trang trước"),
) -> ChatListResponse:
    return await chat_service.get_chats(
        user=current_user,
        limit=limit,
        cursor=cursor,
    )


@router.get("/{chat_id}", response_model=ChatResponse, summary="Get a chat")
async def read_chat(
    chat_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> Chat:
    return await chat_service.get_chat(chat_id, current_user)


@router.put("/{chat_id}", response_model=ChatResponse, summary="Update a chat")
async def update_chat(
    chat_id: int,
    chat_in: ChatUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> Chat:
    return await chat_service.update_chat(chat_id, chat_in, current_user)


@router.delete(
    "/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat",
)
async def delete_chat(
    chat_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    await chat_service.delete_chat(chat_id, current_user)