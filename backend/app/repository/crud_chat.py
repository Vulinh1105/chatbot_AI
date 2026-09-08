from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.model.chat import Chat
from app.schemas.chat import ChatCreate, ChatUpdate


class CRUDChat:

  async def get_multi_by_user(
      self,
      db: AsyncSession,
      *,
      user_id: int,
      is_superuser: bool,
      skip: int = 0,
      limit: int = 100,
  ):
    if is_superuser:
      # Admin thấy tất cả đoạn chat
      result = await db.execute(select(Chat).offset(skip).limit(limit))
    else:
      # User thường chỉ thấy đoạn chat của chính mình
      result = await db.execute(
          select(Chat)
          .filter(Chat.owner_id == user_id)
          .offset(skip)
          .limit(limit)
      )
    return result.scalars().all()

  async def create_with_owner(
      self, db: AsyncSession, *, obj_in: ChatCreate, user_id: int
  ):
    db_obj = Chat(title=obj_in.title, owner_id=user_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

  async def get_by_id(self, db: AsyncSession, *, chat_id: int):
    result = await db.execute(select(Chat).filter(Chat.id == chat_id))
    return result.scalars().first()

  async def update(
      self,
      db: AsyncSession,
      *,
      db_obj: Chat,
      obj_in: ChatUpdate,
      user_id: int,
      is_superuser: bool,
  ):
    # Kiểm tra quyền: Phải là chủ sở hữu hoặc là Admin
    if not is_superuser and db_obj.owner_id != user_id:
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Không có quyền chỉnh sửa đoạn chat này",
      )
    db_obj.title = obj_in.title
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

  async def remove(
      self,
      db: AsyncSession,
      *,
      chat_id: int,
      user_id: int,
      is_superuser: bool,
  ):
    db_obj = await self.get_by_id(db, chat_id=chat_id)
    if not db_obj:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Không tìm thấy đoạn chat",
      )
    if not is_superuser and db_obj.owner_id != user_id:
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Không có quyền xóa đoạn chat này",
      )
    await db.delete(db_obj)
    await db.commit()
    return db_obj


chat = CRUDChat()