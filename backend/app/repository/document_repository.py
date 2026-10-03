from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.document import (
    Document,
    DocumentVersion,
    UploadSession,
    UploadPart,
    UploadSessionStatus,
    DocumentIndexJob,
    IndexJobStatus,
)


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Document CRUD ---
    async def create_document(self, owner_id: int, title: str, description: Optional[str] = None) -> Document:
        doc = Document(owner_id=owner_id, title=title, description=description)
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get_document_by_id(self, document_id: int, owner_id: Optional[int] = None) -> Optional[Document]:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.current_version),
                selectinload(Document.versions),
            )
            .where(Document.id == document_id, Document.is_deleted == False)
        )
        if owner_id is not None:
            stmt = stmt.where(Document.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(self, owner_id: int, skip: int = 0, limit: int = 50) -> List[Document]:
        stmt = (
            select(Document)
            .options(selectinload(Document.current_version))
            .where(Document.owner_id == owner_id, Document.is_deleted == False)
            .order_by(Document.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete_document(self, document_id: int, owner_id: int) -> bool:
        doc = await self.get_document_by_id(document_id, owner_id)
        if not doc:
            return False
        doc.is_deleted = True
        await self.session.commit()
        return True

    # --- Document Version CRUD ---
    async def get_next_version_number(self, document_id: int) -> int:
        stmt = select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(
            DocumentVersion.document_id == document_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() + 1

    async def create_version(
        self,
        document_id: int,
        version_number: int,
        original_filename: str,
        size_bytes: int,
        object_key: str,
        content_type: Optional[str] = None,
        etag: Optional[str] = None,
        checksum_sha256: Optional[str] = None,
    ) -> DocumentVersion:
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            object_key=object_key,
            etag=etag,
            checksum_sha256=checksum_sha256,
        )
        self.session.add(version)
        await self.session.flush()

        # Cập nhật current_version_id cho Document cha
        doc = await self.get_document_by_id(document_id)
        if doc:
            doc.current_version_id = version.id

        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def get_version_by_number(self, document_id: int, version_number: int) -> Optional[DocumentVersion]:
        stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.version_number == version_number,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # --- Upload Session Management ---
    async def create_upload_session(
        self,
        session_id: str,
        owner_id: int,
        filename: str,
        total_size_bytes: int,
        chunk_size_bytes: int,
        total_parts: int,
        object_key: str,
        s3_upload_id: str,
        expires_at: datetime,
        document_id: Optional[int] = None,
        content_type: str = "application/octet-stream",
    ) -> UploadSession:
        session = UploadSession(
            id=session_id,
            owner_id=owner_id,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            total_size_bytes=total_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
            total_parts=total_parts,
            object_key=object_key,
            s3_upload_id=s3_upload_id,
            expires_at=expires_at,
            status=UploadSessionStatus.PENDING,
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def get_upload_session(self, session_id: str) -> Optional[UploadSession]:
        stmt = (
            select(UploadSession)
            .options(selectinload(UploadSession.parts))
            .where(UploadSession.id == session_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_upload_part(
        self,
        session_id: str,
        part_number: int,
        etag: str,
        size_bytes: int,
    ) -> UploadPart:
        part = UploadPart(
            session_id=session_id,
            part_number=part_number,
            etag=etag,
            size_bytes=size_bytes,
        )
        self.session.add(part)

        # Đổi status session sang UPLOADING nếu đang PENDING
        session = await self.get_upload_session(session_id)
        if session and session.status == UploadSessionStatus.PENDING:
            session.status = UploadSessionStatus.UPLOADING

        await self.session.commit()
        await self.session.refresh(part)
        return part

    async def update_session_status(self, session_id: str, status: UploadSessionStatus) -> None:
        session = await self.get_upload_session(session_id)
        if session:
            session.status = status
            await self.session.commit()