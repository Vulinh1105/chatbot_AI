from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.model.document import UploadSessionStatus, IndexJobStatus


# --- Version Schemas ---
class DocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version_number: int
    original_filename: str
    content_type: Optional[str] = None
    size_bytes: int
    object_key: str
    etag: Optional[str] = None
    checksum_sha256: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Document Schemas ---
class DocumentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    owner_id: int
    title: str
    description: Optional[str] = None
    is_deleted: bool
    current_version_id: Optional[int] = None
    current_version: Optional[DocumentVersionResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    versions: List[DocumentVersionResponse] = []


# --- Multipart Upload Schemas ---
class InitUploadRequest(BaseModel):
    filename: str = Field(..., max_length=255)
    total_size_bytes: int = Field(..., gt=0)
    chunk_size_bytes: int = Field(default=10 * 1024 * 1024)  # 10 MiB mặc định
    content_type: Optional[str] = "application/octet-stream"
    document_id: Optional[int] = None  # None: tạo doc mới; có ID: tạo version mới


class InitUploadResponse(BaseModel):
    session_id: str
    object_key: str
    chunk_size_bytes: int
    total_parts: int
    expires_at: datetime


class UploadPartResponse(BaseModel):
    session_id: str
    part_number: int
    etag: str
    size_bytes: int


class CompleteUploadRequest(BaseModel):
    parts: Optional[List[dict]] = None  # None: server tự lấy từ DB/MinIO


class CompleteUploadResponse(BaseModel):
    document_id: int
    version_id: int
    version_number: int
    status: str = "COMPLETED"


class UploadSessionStatusResponse(BaseModel):
    session_id: str
    status: UploadSessionStatus
    total_parts: int
    uploaded_parts: List[int]
    expires_at: datetime

    class Config:
        from_attributes = True