from pathlib import Path
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import (
    get_current_user,
    get_current_admin_user,
    get_document_service,
    is_admin_user,
)
from app.model.document import Document
from app.model.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter()
ALLOWED_FILE_EXTENSIONS = frozenset({".docx", ".pdf", ".csv", ".txt"})


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "unnamed").name.strip()
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    if Path(name).suffix.lower() not in ALLOWED_FILE_EXTENSIONS:
        allowed_extensions = ", ".join(sorted(ALLOWED_FILE_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed extensions: {allowed_extensions}",
        )
    return name[:255]


@router.get("/", response_model=list[DocumentResponse], summary="List accessible documents")
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> Sequence[Document]:
    owner_id = None if is_admin_user(current_user) else current_user.id
    return await document_service.list_documents(owner_id=owner_id, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin upload tài liệu",
)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> Document:
    content = await file.read()
    return await document_service.create_document(
        owner_id=current_admin.id,
        original_filename=_safe_filename(file.filename),
        content_type=file.content_type,
        content=content,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> Document:
    return await document_service.get_document(document_id, current_user.id, is_admin_user(current_user))


@router.put("/{document_id}", response_model=DocumentResponse)
async def replace_document(
    document_id: int,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> Document:
    document = await document_service.get_document(document_id, current_user.id, is_admin_user(current_user))
    return await document_service.replace_document(
        document,
        original_filename=_safe_filename(file.filename),
        content_type=file.content_type,
        content=await file.read(),
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    document = await document_service.get_document(document_id, current_user.id, is_admin_user(current_user))
    await document_service.delete_document(document)


@router.get("/{document_id}/download", response_class=FileResponse)
async def download_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> FileResponse:
    document = await document_service.get_document(document_id, current_user.id, is_admin_user(current_user))
    file_path = Path(document.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")
    return FileResponse(
        file_path,
        media_type=document.content_type or "application/octet-stream",
        filename=document.original_filename,
    )