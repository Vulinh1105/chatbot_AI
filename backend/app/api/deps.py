from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.authorization import is_admin_user
from app.database import get_db
from app.model.user import User

from app.repository.chat_repository import ChatRepository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.repository.document_repository import DocumentRepository
from app.repository.user_repository import UserRepository
from app.services.document_service import DocumentService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_str}/auth/login")


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    """Create a repository bound to the current request's database session."""
    return UserRepository(db)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(user_repo)


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(user_repo)


def get_chat_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatRepository:
    return ChatRepository(db)


def get_chat_service(
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)],
) -> ChatService:
    return ChatService(chat_repo)
  
  
def get_document_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRepository:
    return DocumentRepository(db)


def get_document_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentService:
    from pathlib import Path

    return DocumentService(document_repo, Path(settings.documents_dir))


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve the authenticated user through the auth service."""
    return await auth_service.get_current_user_by_token(token)

  
async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation",
        )
    return current_user
