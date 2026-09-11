from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.document import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, document_id: int) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalars().first()

    async def get_multi(
        self,
        *,
        owner_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        query = select(Document).order_by(Document.id).offset(skip).limit(limit)
        if owner_id is not None:
            query = query.where(Document.owner_id == owner_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, **values: object) -> Document:
        document = Document(**values)
        self.db.add(document)
        await self._commit()
        await self.db.refresh(document)
        return document

    async def update(self, document: Document, **values: object) -> Document:
        for field, value in values.items():
            setattr(document, field, value)
        await self._commit()
        await self.db.refresh(document)
        return document

    async def delete(self, document: Document) -> None:
        await self.db.delete(document)
        await self._commit()

    async def _commit(self) -> None:
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise