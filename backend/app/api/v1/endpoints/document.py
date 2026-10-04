from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.model.user import User
from app.repository.document_repository import DocumentRepository
from app.schemas.document import (
    CompleteUploadRequest,
    CompleteUploadResponse,
    DocumentDetailResponse,
    DocumentResponse,
    DocumentVersionResponse,
    InitUploadRequest,
    InitUploadResponse,
    UploadPartResponse,
    UploadSessionStatusResponse,
)
from app.services.document_service import DocumentService
from app.services.storage_service import storage_service

router = APIRouter()


# --- Multipart Upload Endpoints ---
@router.post("/upload/init", response_model=InitUploadResponse)
async def init_multipart_upload(
    req: InitUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.init_upload(user_id=current_user.id, req=req)


@router.post("/upload/{session_id}/part", response_model=UploadPartResponse)
async def upload_document_part(
    session_id: str,
    part_number: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    data = await file.read()
    return await service.upload_part(
        session_id=session_id,
        part_number=part_number,
        data=data,
        user_id=current_user.id,
    )


@router.post("/upload/{session_id}/complete", response_model=CompleteUploadResponse)
async def complete_multipart_upload(
    session_id: str,
    req: Optional[CompleteUploadRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.complete_upload(session_id=session_id, user_id=current_user.id)


@router.get("/upload/{session_id}/status", response_model=UploadSessionStatusResponse)
async def get_upload_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    session = await repo.get_upload_session(session_id)
    if not session or session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên tải lên không tồn tại hoặc bạn không có quyền truy cập."
        )

    uploaded_parts = [p.part_number for p in session.parts]
    return UploadSessionStatusResponse(
        session_id=session.id,
        status=session.status,
        total_parts=session.total_parts,
        uploaded_parts=uploaded_parts,
        expires_at=session.expires_at,
    )


# --- Document Management Endpoints ---
@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    return await repo.list_documents(owner_id=current_user.id, skip=skip, limit=limit)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document_detail(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    doc = await repo.get_document_by_id(document_id=document_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài liệu."
        )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    success = await repo.soft_delete_document(document_id=document_id, owner_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài liệu để xóa."
        )
    return None


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    version: Optional[int] = Query(None, description="Version number cần tải; bỏ trống để tải bản mới nhất"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    doc = await repo.get_document_by_id(document_id=document_id, owner_id=current_user.id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu.")

    target_version: Optional[DocumentVersionResponse] = None
    if version is not None:
        target_version = await repo.get_version_by_number(document_id=doc.id, version_number=version)
    else:
        target_version = doc.current_version

    if not target_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phiên bản tài liệu không tồn tại.")

    # Sinh link presigned URL từ MinIO tải trực tiếp
    download_url = storage_service.generate_presigned_download_url(
        object_name=target_version.object_key,
        original_filename=target_version.original_filename,
        expires_seconds=3600,
    )
    return RedirectResponse(url=download_url)