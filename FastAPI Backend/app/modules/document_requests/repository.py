from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.document_requests.models import DocumentRequest, DocumentRequestDocument, DocumentRequestStatus


class DocumentRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: DocumentRequest) -> DocumentRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> DocumentRequest | None:
        result = await self.db.execute(
            select(DocumentRequest)
            .options(
                selectinload(DocumentRequest.client),
                selectinload(DocumentRequest.matter),
                selectinload(DocumentRequest.assignee),
            )
            .where(DocumentRequest.id == request_id, DocumentRequest.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        assigned_to: UUID | None = None,
        status: DocumentRequestStatus | None = None,
        priority: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[DocumentRequest], int]:
        query = (
            select(DocumentRequest)
            .options(
                selectinload(DocumentRequest.client),
                selectinload(DocumentRequest.matter),
                selectinload(DocumentRequest.assignee),
            )
            .where(DocumentRequest.tenant_id == tenant_id)
        )
        count_query = select(func.count(DocumentRequest.id)).where(DocumentRequest.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                DocumentRequest.title.ilike(f"%{search}%"),
                DocumentRequest.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(DocumentRequest.client_id == client_id)
            count_query = count_query.where(DocumentRequest.client_id == client_id)

        if matter_id:
            query = query.where(DocumentRequest.matter_id == matter_id)
            count_query = count_query.where(DocumentRequest.matter_id == matter_id)

        if assigned_to:
            query = query.where(DocumentRequest.assigned_to == assigned_to)
            count_query = count_query.where(DocumentRequest.assigned_to == assigned_to)

        if status:
            query = query.where(DocumentRequest.status == status)
            count_query = count_query.where(DocumentRequest.status == status)

        if date_from:
            query = query.where(DocumentRequest.due_date >= date_from)
            count_query = count_query.where(DocumentRequest.due_date >= date_from)

        if date_to:
            query = query.where(DocumentRequest.due_date <= date_to)
            count_query = count_query.where(DocumentRequest.due_date <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(DocumentRequest, sort_by):
            sort_column = getattr(DocumentRequest, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(DocumentRequest.due_date.asc().nullslast(), DocumentRequest.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_documents(self, request_id: UUID, tenant_id: UUID) -> list[DocumentRequestDocument]:
        result = await self.db.execute(
            select(DocumentRequestDocument).where(
                DocumentRequestDocument.request_id == request_id,
                DocumentRequestDocument.tenant_id == tenant_id,
            )
        )
        return list(result.scalars().all())

    async def add_document(self, document: DocumentRequestDocument) -> DocumentRequestDocument:
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def update(self, request: DocumentRequest) -> DocumentRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def delete(self, request: DocumentRequest) -> None:
        await self.db.delete(request)
        await self.db.flush()