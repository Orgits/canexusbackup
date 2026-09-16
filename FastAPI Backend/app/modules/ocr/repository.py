from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ocr.models import OCRJob, OCRTemplate, OCRStatus


class OCRJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, job: OCRJob) -> OCRJob:
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID, tenant_id: UUID) -> OCRJob | None:
        result = await self.db.execute(
            select(OCRJob).where(OCRJob.id == job_id, OCRJob.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list[OCRJob]:
        result = await self.db.execute(
            select(OCRJob).where(
                OCRJob.document_id == document_id,
                OCRJob.tenant_id == tenant_id,
            ).order_by(OCRJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        engine: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[OCRJob], int]:
        from sqlalchemy import func, select

        query = select(OCRJob).where(OCRJob.tenant_id == tenant_id)
        count_query = select(func.count(OCRJob.id)).where(OCRJob.tenant_id == tenant_id)

        if status:
            query = query.where(OCRJob.status == status)
            count_query = count_query.where(OCRJob.status == status)

        if engine:
            query = query.where(OCRJob.engine == engine)
            count_query = count_query.where(OCRJob.engine == engine)

        if date_from:
            query = query.where(OCRJob.created_at >= date_from)
            count_query = count_query.where(OCRJob.created_at >= date_from)

        if date_to:
            query = query.where(OCRJob.created_at <= date_to)
            count_query = count_query.where(OCRJob.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(OCRJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, job: OCRJob) -> OCRJob:
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def delete(self, job: OCRJob) -> None:
        await self.db.delete(job)
        await self.db.flush()


class OCRTemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, template: OCRTemplate) -> OCRTemplate:
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_by_id(self, template_id: UUID, tenant_id: UUID) -> OCRTemplate | None:
        from sqlalchemy import select
        result = await self.db.execute(
            select(OCRTemplate).where(OCRTemplate.id == template_id, OCRTemplate.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, tenant_id: UUID) -> OCRTemplate | None:
        from sqlalchemy import select
        result = await self.db.execute(
            select(OCRTemplate).where(OCRTemplate.name == name, OCRTemplate.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engine: str | None = None,
        is_active: bool | None = None,
        is_default: bool | None = None,
    ) -> tuple[list, int]:
        from sqlalchemy import func, select

        query = select(OCRTemplate).where(OCRTemplate.tenant_id == tenant_id)
        count_query = select(func.count(OCRTemplate.id)).where(OCRTemplate.tenant_id == tenant_id)

        if engine:
            query = query.where(OCRTemplate.engine == engine)
            count_query = count_query.where(OCRTemplate.engine == engine)

        if is_active is not None:
            query = query.where(OCRTemplate.is_active == is_active)
            count_query = count_query.where(OCRTemplate.is_active == is_active)

        if is_default is not None:
            query = query.where(OCRTemplate.is_default == is_default)
            count_query = count_query.where(OCRTemplate.is_default == is_default)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(OCRTemplate.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, template: OCRTemplate) -> OCRTemplate:
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete(self, template: OCRTemplate) -> None:
        await self.db.delete(template)
        await self.db.flush()