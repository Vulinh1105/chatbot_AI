from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base  # Trỏ tới file database.py trong thư mục app


class Chat(Base):
  __tablename__ = "chats"

  id = Column(Integer, primary_key=True, index=True)
  owner_id = Column(
      Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
  )
  title = Column(String, index=True, nullable=False)
  created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
  updated_at = Column(
      DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
  )

  # Liên kết với bảng User
  owner = relationship("User", back_populates="chats")