from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UploadSessionStatus(str, enum.Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    EXPIRED = "EXPIRED"


class IndexJobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    current_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Quan hệ
    versions: Mapped[List[DocumentVersion]] = relationship(
        "DocumentVersion",
        back_populates="document",
        foreign_keys="DocumentVersion.document_id",
        cascade="all, delete-orphan",
        order_by="desc(DocumentVersion.version_number)",
    )
    current_version: Mapped[Optional[DocumentVersion]] = relationship(
        "DocumentVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )
    upload_sessions: Mapped[List[UploadSession]] = relationship(
        "UploadSession",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Metadata file lưu trên MinIO
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    etag: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Quan hệ
    document: Mapped[Document] = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )
    index_jobs: Mapped[List[DocumentIndexJob]] = relationship(
        "DocumentIndexJob",
        back_populates="version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_doc_version_unique", "document_id", "version_number", unique=True),
    )


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # session_id (UUID4)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), default="application/octet-stream")
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chunk_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # MinIO S3 Multipart tracking
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    s3_upload_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    status: Mapped[UploadSessionStatus] = mapped_column(
        Enum(UploadSessionStatus, name="upload_session_status_enum"),
        default=UploadSessionStatus.PENDING,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    document: Mapped[Optional[Document]] = relationship(
        "Document",
        back_populates="upload_sessions",
    )
    parts: Mapped[List[UploadPart]] = relationship(
        "UploadPart",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="UploadPart.part_number",
    )


class UploadPart(Base):
    __tablename__ = "upload_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    etag: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[UploadSession] = relationship("UploadSession", back_populates="parts")

    __table_args__ = (
        Index("ix_session_part_unique", "session_id", "part_number", unique=True),
    )


class DocumentIndexJob(Base):
    __tablename__ = "document_index_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[IndexJobStatus] = mapped_column(
        Enum(IndexJobStatus, name="index_job_status_enum"),
        default=IndexJobStatus.QUEUED,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    version: Mapped[DocumentVersion] = relationship(
        "DocumentVersion",
        back_populates="index_jobs",
    )