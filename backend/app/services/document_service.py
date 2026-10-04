from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import BinaryIO, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.document import Document, DocumentVersion, UploadSession, UploadSessionStatus
from app.repository.document_repository import DocumentRepository
from app.schemas.document import (
    InitUploadRequest,
    InitUploadResponse,
    UploadPartResponse,
    CompleteUploadResponse,
)
from app.services.storage_service import storage_service


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)

    async def init_upload(self, user_id: int, req: InitUploadRequest) -> InitUploadResponse:
        if req.document_id:
            doc = await self.repo.get_document_by_id(req.document_id, owner_id=user_id)
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy tài liệu để cập nhật phiên bản mới."
                )

        session_id = str(uuid.uuid4())
        total_parts = math.ceil(req.total_size_bytes / req.chunk_size_bytes)
        if total_parts == 0:
            total_parts = 1

        clean_filename = req.filename.replace(" ", "_")
        object_key = f"users/{user_id}/documents/{session_id}/{clean_filename}"

        # Sửa: đổi object_name -> object_key
        s3_upload_id = storage_service.create_multipart_upload(
            object_key=object_key,
            content_type=req.content_type or "application/octet-stream"
        )

        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        await self.repo.create_upload_session(
            session_id=session_id,
            owner_id=user_id,
            document_id=req.document_id,
            filename=req.filename,
            content_type=req.content_type or "application/octet-stream",
            total_size_bytes=req.total_size_bytes,
            chunk_size_bytes=req.chunk_size_bytes,
            total_parts=total_parts,
            object_key=object_key,
            s3_upload_id=s3_upload_id,
            expires_at=expires_at,
        )

        return InitUploadResponse(
            session_id=session_id,
            object_key=object_key,
            chunk_size_bytes=req.chunk_size_bytes,
            total_parts=total_parts,
            expires_at=expires_at,
        )

    async def upload_part(
        self,
        session_id: str,
        part_number: int,
        data: bytes,
        user_id: int,
    ) -> UploadPartResponse:
        session = await self.repo.get_upload_session(session_id)
        if not session or session.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session không tồn tại hoặc bạn không có quyền truy cập."
            )

        if session.status in [UploadSessionStatus.COMPLETED, UploadSessionStatus.ABORTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload session đã kết thúc với trạng thái: {session.status.value}"
            )

        # Sửa: đổi object_name -> object_key
        etag = storage_service.upload_part(
            object_key=session.object_key,
            upload_id=session.s3_upload_id,
            part_number=part_number,
            data=data,
        )

        await self.repo.add_upload_part(
            session_id=session.id,
            part_number=part_number,
            etag=etag,
            size_bytes=len(data),
        )

        return UploadPartResponse(
            session_id=session_id,
            part_number=part_number,
            etag=etag,
            size_bytes=len(data),
        )

    async def complete_upload(
        self,
        session_id: str,
        user_id: int,
    ) -> CompleteUploadResponse:
        session = await self.repo.get_upload_session(session_id)
        if not session or session.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session không tồn tại hoặc bạn không có quyền truy cập."
            )

        if session.status == UploadSessionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload session này đã được hoàn tất trước đó."
            )

        uploaded_parts = sorted(session.parts, key=lambda p: p.part_number)
        if len(uploaded_parts) < session.total_parts:
            missing = set(range(1, session.total_parts + 1)) - {p.part_number for p in uploaded_parts}
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chưa tải đủ các parts. Còn thiếu các parts: {sorted(list(missing))}"
            )

        parts_manifest = [
            {"PartNumber": p.part_number, "ETag": p.etag}
            for p in uploaded_parts
        ]

        # Sửa: đổi object_name -> object_key
        storage_service.complete_multipart_upload(
            object_key=session.object_key,
            upload_id=session.s3_upload_id,
            parts=parts_manifest,
        )

        if session.document_id:
            doc = await self.repo.get_document_by_id(session.document_id, owner_id=user_id)
            if not doc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu gốc.")
            version_number = await self.repo.get_next_version_number(doc.id)
        else:
            doc = await self.repo.create_document(
                owner_id=user_id,
                title=session.filename,
                description=None,
            )
            version_number = 1

        version = await self.repo.create_version(
            document_id=doc.id,
            version_number=version_number,
            original_filename=session.filename,
            size_bytes=session.total_size_bytes,
            object_key=session.object_key,
            content_type=session.content_type,
        )

        await self.repo.update_session_status(session_id, UploadSessionStatus.COMPLETED)

        return CompleteUploadResponse(
            document_id=doc.id,
            version_id=version.id,
            version_number=version.version_number,
            status="COMPLETED",
        )