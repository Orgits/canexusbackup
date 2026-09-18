from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.engagement_documents.models import (
    EngagementDocument,
    EngagementDocumentSigner,
    EngagementDocumentVersion,
    EngagementDocumentTemplate,
    EngagementDocumentStatus,
)


class EngagementDocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, doc: EngagementDocument) -> EngagementDocument:
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: UUID, tenant_id: UUID) -> EngagementDocument | None:
        result = await self.db.execute(
            select(EngagementDocument)
            .options(
                selectinload(EngagementDocument.client),
                selectinload(EngagementDocument.matter),
                selectinload(EngagementDocument.engagement_partner),
                selectinload(EngagementDocument.engagement_manager),
            )
            .where(EngagementDocument.id == doc_id, EngagementDocument.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, document_number: str, tenant_id: UUID) -> EngagementDocument | None:
        result = await self.db.execute(
            select(EngagementDocument).where(
                EngagementDocument.document_number == document_number,
                EngagementDocument.tenant_id == tenant_id,
            )
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
        status: str | None = None,
        document_type: str | None = None,
        engagement_partner_id: UUID | None = None,
        engagement_manager_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[EngagementDocument], int]:
        query = select(EngagementDocument).where(EngagementDocument.tenant_id == tenant_id)
        count_query = select(func.count(EngagementDocument.id)).where(EngagementDocument.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    EngagementDocument.document_number.ilike(search_term),
                    EngagementDocument.title.ilike(search_term),
                    EngagementDocument.description.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    EngagementDocument.document_number.ilike(search_term),
                    EngagementDocument.title.ilike(search_term),
                    EngagementDocument.description.ilike(search_term),
                )
            )

        if client_id:
            query = query.where(EngagementDocument.client_id == client_id)
            count_query = count_query.where(EngagementDocument.client_id == client_id)

        if matter_id:
            query = query.where(EngagementDocument.matter_id == matter_id)
            count_query = count_query.where(EngagementDocument.matter_id == matter_id)

        if status:
            query = query.where(EngagementDocument.status == status)
            count_query = count_query.where(EngagementDocument.status == status)

        if document_type:
            query = query.where(EngagementDocument.document_type == document_type)
            count_query = count_query.where(EngagementDocument.document_type == document_type)

        if engagement_partner_id:
            query = query.where(EngagementDocument.engagement_partner_id == engagement_partner_id)
            count_query = count_query.where(EngagementDocument.engagement_partner_id == engagement_partner_id)

        if engagement_manager_id:
            query = query.where(EngagementDocument.engagement_manager_id == engagement_manager_id)
            count_query = count_query.where(EngagementDocument.engagement_manager_id == engagement_manager_id)

        if date_from:
            query = query.where(EngagementDocument.created_at >= date_from)
            count_query = count_query.where(EngagementDocument.created_at >= date_from)

        if date_to:
            query = query.where(EngagementDocument.created_at <= date_to)
            count_query = count_query.where(EngagementDocument.created_at <= date_to)

        sort_column = getattr(EngagementDocument, sort_by, EngagementDocument.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(EngagementDocument.client),
                selectinload(EngagementDocument.matter),
                selectinload(EngagementDocument.engagement_partner),
                selectinload(EngagementDocument.engagement_manager),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, doc: EngagementDocument) -> EngagementDocument:
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def delete(self, doc: EngagementDocument) -> None:
        await self.db.delete(doc)
        await self.db.flush()


class EngagementDocumentSignerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, signer: EngagementDocumentSigner) -> EngagementDocumentSigner:
        self.db.add(signer)
        await self.db.flush()
        await self.db.refresh(signer)
        return signer

    async def get_by_id(self, signer_id: UUID, tenant_id: UUID) -> EngagementDocumentSigner | None:
        result = await self.db.execute(
            select(EngagementDocumentSigner)
            .options(
                selectinload(EngagementDocumentSigner.engagement_document),
                selectinload(EngagementDocumentSigner.signer),
            )
            .where(EngagementDocumentSigner.id == signer_id, EngagementDocumentSigner.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_document(self, doc_id: UUID, tenant_id: UUID) -> list[EngagementDocumentSigner]:
        result = await self.db.execute(
            select(EngagementDocumentSigner)
            .options(selectinload(EngagementDocumentSigner.signer))
            .where(
                EngagementDocumentSigner.engagement_document_id == doc_id,
                EngagementDocumentSigner.tenant_id == tenant_id,
            )
            .order_by(EngagementDocumentSigner.signing_order.asc())
        )
        return list(result.scalars().all())

    async def update(self, signer: EngagementDocumentSigner) -> EngagementDocumentSigner:
        await self.db.flush()
        await self.db.refresh(signer)
        return signer

    async def delete(self, signer: EngagementDocumentSigner) -> None:
        await self.db.delete(signer)
        await self.db.flush()


class EngagementDocumentVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, version: EngagementDocumentVersion) -> EngagementDocumentVersion:
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def get_by_id(self, version_id: UUID, tenant_id: UUID) -> EngagementDocumentVersion | None:
        result = await self.db.execute(
            select(EngagementDocumentVersion)
            .options(
                selectinload(EngagementDocumentVersion.engagement_document),
                selectinload(EngagementDocumentVersion.created_by),
            )
            .where(EngagementDocumentVersion.id == version_id, EngagementDocumentVersion.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_document(self, doc_id: UUID, tenant_id: UUID) -> list[EngagementDocumentVersion]:
        result = await self.db.execute(
            select(EngagementDocumentVersion)
            .options(selectinload(EngagementDocumentVersion.created_by))
            .where(
                EngagementDocumentVersion.engagement_document_id == doc_id,
                EngagementDocumentVersion.tenant_id == tenant_id,
            )
            .order_by(EngagementDocumentVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_latest_version(self, doc_id: UUID, tenant_id: UUID) -> EngagementDocumentVersion | None:
        result = await self.db.execute(
            select(EngagementDocumentVersion)
            .where(
                EngagementDocumentVersion.engagement_document_id == doc_id,
                EngagementDocumentVersion.tenant_id == tenant_id,
            )
            .order_by(EngagementDocumentVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, version: EngagementDocumentVersion) -> EngagementDocumentVersion:
        await self.db.flush()
        await self.db.refresh(version)
        return version


class EngagementDocumentTemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, template: EngagementDocumentTemplate) -> EngagementDocumentTemplate:
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_by_id(self, template_id: UUID, tenant_id: UUID) -> EngagementDocumentTemplate | None:
        result = await self.db.execute(
            select(EngagementDocumentTemplate)
            .options(selectinload(EngagementDocumentTemplate.created_by))
            .where(EngagementDocumentTemplate.id == template_id, EngagementDocumentTemplate.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_type(self, document_type: str, tenant_id: UUID) -> list[EngagementDocumentTemplate]:
        result = await self.db.execute(
            select(EngagementDocumentTemplate)
            .options(selectinload(EngagementDocumentTemplate.created_by))
            .where(
                EngagementDocumentTemplate.document_type == document_type,
                EngagementDocumentTemplate.tenant_id == tenant_id,
                EngagementDocumentTemplate.is_active == True,
            )
            .order_by(EngagementDocumentTemplate.is_default.desc(), EngagementDocumentTemplate.version.desc())
        )
        return list(result.scalars().all())

    async def get_default(self, document_type: str, tenant_id: UUID) -> EngagementDocumentTemplate | None:
        result = await self.db.execute(
            select(EngagementDocumentTemplate)
            .where(
                EngagementDocumentTemplate.document_type == document_type,
                EngagementDocumentTemplate.tenant_id == tenant_id,
                EngagementDocumentTemplate.is_default == True,
                EngagementDocumentTemplate.is_active == True,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        document_type: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[EngagementDocumentTemplate], int]:
        query = select(EngagementDocumentTemplate).where(EngagementDocumentTemplate.tenant_id == tenant_id)
        count_query = select(func.count(EngagementDocumentTemplate.id)).where(EngagementDocumentTemplate.tenant_id == tenant_id)

        if document_type:
            query = query.where(EngagementDocumentTemplate.document_type == document_type)
            count_query = count_query.where(EngagementDocumentTemplate.document_type == document_type)

        if is_active is not None:
            query = query.where(EngagementDocumentTemplate.is_active == is_active)
            count_query = count_query.where(EngagementDocumentTemplate.is_active == is_active)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    EngagementDocumentTemplate.name.ilike(search_term),
                    EngagementDocumentTemplate.description.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    EngagementDocumentTemplate.name.ilike(search_term),
                    EngagementDocumentTemplate.description.ilike(search_term),
                )
            )

        sort_column = getattr(EngagementDocumentTemplate, sort_by, EngagementDocumentTemplate.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(selectinload(EngagementDocumentTemplate.created_by))
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, template: EngagementDocumentTemplate) -> EngagementDocumentTemplate:
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete(self, template: EngagementDocumentTemplate) -> None:
        await self.db.delete(template)
        await self.db.flush()