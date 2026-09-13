from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.documents.models import Document, DocumentStatus, DocumentCategory


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, document: Document) -> Document:
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def get_by_id(self, document_id: UUID, tenant_id: UUID) -> Optional[Document]:
        result = await self.db.execute(
            select(Document)
            .options(
                selectinload(Document.client),
                selectinload(Document.matter),
                selectinload(Document.task),
                selectinload(Document.compliance_cycle),
                selectinload(Document.uploaded_by_user),
            )
            .where(Document.id == document_id, Document.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        matter_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        compliance_cycle_id: Optional[UUID] = None,
        status: Optional[DocumentStatus] = None,
        category: Optional[DocumentCategory] = None,
        uploaded_by: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Document], int]:
        from datetime import datetime
        query = (
            select(Document)
            .options(
                selectinload(Document.client),
                selectinload(Document.matter),
                selectinload(Document.task),
                selectinload(Document.compliance_cycle),
                selectinload(Document.uploaded_by_user),
            )
            .where(Document.tenant_id == tenant_id, Document.is_latest_version == True)
        )
        count_query = select(func.count(Document.id)).where(Document.tenant_id == tenant_id, Document.is_latest_version == True)

        if search:
            search_filter = or_(
                Document.filename.ilike(f"%{search}%"),
                Document.original_filename.ilike(f"%{search}%"),
                Document.title.ilike(f"%{search}%"),
                Document.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(Document.client_id == client_id)
            count_query = count_query.where(Document.client_id == client_id)

        if matter_id:
            query = query.where(Document.matter_id == matter_id)
            count_query = count_query.where(Document.matter_id == matter_id)

        if task_id:
            query = query.where(Document.task_id == task_id)
            count_query = count_query.where(Document.task_id == task_id)

        if compliance_cycle_id:
            query = query.where(Document.compliance_cycle_id == compliance_cycle_id)
            count_query = count_query.where(Document.compliance_cycle_id == compliance_cycle_id)

        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)

        if category:
            query = query.where(Document.category == category)
            count_query = count_query.where(Document.category == category)

        if uploaded_by:
            query = query.where(Document.uploaded_by == uploaded_by)
            count_query = count_query.where(Document.uploaded_by == uploaded_by)

        if date_from:
            query = query.where(Document.created_at >= date_from)
            count_query = count_query.where(Document.created_at >= date_from)

        if date_to:
            query = query.where(Document.created_at <= date_to)
            count_query = count_query.where(Document.created_at <= date_to)

        if tags:
            query = query.where(Document.tags.contains(tags))
            count_query = count_query.where(Document.tags.contains(tags))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Document, sort_by):
            sort_column = getattr(Document, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Document.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, document: Document) -> Document:
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def delete(self, document: Document) -> None:
        await self.db.delete(document)
        await self.db.flush()

    async def create_version(self, document: Document) -> Document:
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document