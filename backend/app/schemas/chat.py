from datetime import datetime
from pydantic import BaseModel


# Khung cơ sở chứa tiêu đề chat
class ChatBase(BaseModel):
  title: str


# Khung dùng khi người dùng gửi yêu cầu TẠO chat mới
class ChatCreate(ChatBase):
  pass


# Khung dùng khi người dùng SỬA tiêu đề chat
class ChatUpdate(ChatBase):
  title: str


# Khung trả về dữ liệu chat cho người dùng xem
class ChatResponse(ChatBase):
  id: int
  owner_id: int
  created_at: datetime
  updated_at: datetime

  class Config:
    from_attributes = True