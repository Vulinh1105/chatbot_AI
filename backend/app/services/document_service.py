from pathlib import Path
from typing import Sequence

from fastapi import HTTPException, status

from app.model.document import Document
from app.repository.document_repository import DocumentRepository


class DocumentService:
    def __init__(self, document_repo: DocumentRepository, storage_root: Path):
        self.document_repo = document_repo
        self.storage_root = storage_root.resolve()

    async def list_documents(
        self, *, owner_id: int | None, skip: int = 0, limit: int = 100
    ) -> Sequence[Document]:
        return await self.document_repo.get_multi(
            owner_id=owner_id, skip=skip, limit=limit
        )

    async def get_document(self, document_id: int, current_user_id: int, is_admin: bool) -> Document:
        document = await self.document_repo.get_by_id(document_id)
        if document is None or (not is_admin and document.owner_id != current_user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return document

    async def create_document(
        self,
        *,
        owner_id: int,
        original_filename: str,
        content_type: str | None,
        content: bytes,
    ) -> Document:
        owner_dir = self.storage_root / str(owner_id)
        owner_dir.mkdir(parents=True, exist_ok=True)
        document = await self.document_repo.create(
            owner_id=owner_id,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=len(content),
            file_path="",
        )
        file_path = owner_dir / str(document.id)
        file_path.write_bytes(content)
        return await self.document_repo.update(document, file_path=str(file_path))

    async def replace_document(
        self, document: Document, *, original_filename: str, content_type: str | None, content: bytes
    ) -> Document:
        file_path = Path(document.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return await self.document_repo.update(
            document,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=len(content),
        )

    async def delete_document(self, document: Document) -> None:
        file_path = Path(document.file_path)
        if file_path.is_file():
            file_path.unlink()
        await self.document_repo.delete(document)