from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas
from app.api import deps
from app.model.user import User
from app.repository import crud_chat
from app.api.deps import get_current_user
router = APIRouter()


@router.get("/", response_model=List[schemas.ChatResponse])
async def read_chats(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
  """Lấy danh sách đoạn chat. User thường chỉ thấy của mình, Admin thấy tất cả."""
  chats = await crud_chat.chat.get_multi_by_user(
      db,
      user_id=current_user.id,
      is_superuser=current_user.is_superuser,
      skip=skip,
      limit=limit,
  )
  return chats


@router.post("/", response_model=schemas.ChatResponse)
async def create_chat(
    *,
    db: AsyncSession = Depends(deps.get_db),
    chat_in: schemas.ChatCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
  """Tạo mới một đoạn chat."""
  chat = await crud_chat.chat.create_with_owner(
      db, obj_in=chat_in, user_id=current_user.id
  )
  return chat


@router.put("/{chat_id}", response_model=schemas.ChatResponse)
async def update_chat(
    *,
    db: AsyncSession = Depends(deps.get_db),
    chat_id: int,
    chat_in: schemas.ChatUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
  """Cập nhật tiêu đề đoạn chat."""
  chat = await crud_chat.chat.get_by_id(db, chat_id=chat_id)
  if not chat:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Không tìm thấy đoạn chat",
    )
  chat = await crud_chat.chat.update(
      db,
      db_obj=chat,
      obj_in=chat_in,
      user_id=current_user.id,
      is_superuser=current_user.is_superuser,
  )
  return chat


@router.delete("/{chat_id}", response_model=schemas.ChatResponse)
async def delete_chat(
    *,
    db: AsyncSession = Depends(deps.get_db),
    chat_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
  """Xóa đoạn chat."""
  chat = await crud_chat.chat.remove(
      db,
      chat_id=chat_id,
      user_id=current_user.id,
      is_superuser=current_user.is_superuser,
  )
  return chat