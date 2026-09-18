from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.udin.models import UDINRecord, UDINVerificationLog, UDINStatus


class UDINRecordRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, record: UDINRecord) -> UDINRecord:
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_by_id(self, record_id: UUID, tenant_id: UUID) -> UDINRecord | None:
        result = await self.db.execute(
            select(UDINRecord)
            .options(
                selectinload(UDINRecord.professional),
                selectinload(UDINRecord.client),
                selectinload(UDINRecord.matter),
                selectinload(UDINRecord.document),
                selectinload(UDINRecord.verified_by),
                selectinload(UDINRecord.cancelled_by),
            )
            .where(UDINRecord.id == record_id, UDINRecord.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_udin(self, udin: str, tenant_id: UUID) -> UDINRecord | None:
        result = await self.db.execute(
            select(UDINRecord)
            .options(
                selectinload(UDINRecord.professional),
                selectinload(UDINRecord.client),
                selectinload(UDINRecord.matter),
                selectinload(UDINRecord.document),
            )
            .where(UDINRecord.udin == udin, UDINRecord.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_professional(self, professional_id: UUID, tenant_id: UUID) -> list[UDINRecord]:
        result = await self.db.execute(
            select(UDINRecord)
            .where(UDINRecord.professional_id == professional_id, UDINRecord.tenant_id == tenant_id)
            .order_by(UDINRecord.generated_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        professional_id: UUID | None = None,
        status: str | None = None,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        document_id: UUID | None = None,
        financial_year: str | None = None,
        quarter: str | None = None,
        form_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[UDINRecord], int]:
        query = select(UDINRecord).where(UDINRecord.tenant_id == tenant_id)
        count_query = select(func.count(UDINRecord.id)).where(UDINRecord.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    UDINRecord.udin.ilike(search_term),
                    UDINRecord.description.ilike(search_term),
                    UDINRecord.external_reference.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    UDINRecord.udin.ilike(search_term),
                    UDINRecord.description.ilike(search_term),
                    UDINRecord.external_reference.ilike(search_term),
                )
            )

        if professional_id:
            query = query.where(UDINRecord.professional_id == professional_id)
            count_query = count_query.where(UDINRecord.professional_id == professional_id)

        if status:
            query = query.where(UDINRecord.status == status)
            count_query = count_query.where(UDINRecord.status == status)

        if client_id:
            query = query.where(UDINRecord.client_id == client_id)
            count_query = count_query.where(UDINRecord.client_id == client_id)

        if matter_id:
            query = query.where(UDINRecord.matter_id == matter_id)
            count_query = count_query.where(UDINRecord.matter_id == matter_id)

        if document_id:
            query = query.where(UDINRecord.document_id == document_id)
            count_query = count_query.where(UDINRecord.document_id == document_id)

        if financial_year:
            query = query.where(UDINRecord.financial_year == financial_year)
            count_query = count_query.where(UDINRecord.financial_year == financial_year)

        if quarter:
            query = query.where(UDINRecord.quarter == quarter)
            count_query = count_query.where(UDINRecord.quarter == quarter)

        if form_type:
            query = query.where(UDINRecord.form_type == form_type)
            count_query = count_query.where(UDINRecord.form_type == form_type)

        if date_from:
            query = query.where(UDINRecord.generated_at >= date_from)
            count_query = count_query.where(UDINRecord.generated_at >= date_from)

        if date_to:
            query = query.where(UDINRecord.generated_at <= date_to)
            count_query = count_query.where(UDINRecord.generated_at <= date_to)

        sort_column = getattr(UDINRecord, sort_by, UDINRecord.generated_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(UDINRecord.professional),
                selectinload(UDINRecord.client),
                selectinload(UDINRecord.matter),
                selectinload(UDINRecord.document),
                selectinload(UDINRecord.verified_by),
                selectinload(UDINRecord.cancelled_by),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, record: UDINRecord) -> UDINRecord:
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: UDINRecord) -> None:
        await self.db.delete(record)
        await self.db.flush()


class UDINVerificationLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: UDINVerificationLog) -> UDINVerificationLog:
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_by_id(self, log_id: UUID, tenant_id: UUID) -> UDINVerificationLog | None:
        result = await self.db.execute(
            select(UDINVerificationLog)
            .options(
                selectinload(UDINVerificationLog.udin_record),
                selectinload(UDINVerificationLog.verified_by),
            )
            .where(UDINVerificationLog.id == log_id, UDINVerificationLog.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_udin_record(self, udin_record_id: UUID, tenant_id: UUID) -> list[UDINVerificationLog]:
        result = await self.db.execute(
            select(UDINVerificationLog)
            .where(
                UDINVerificationLog.udin_record_id == udin_record_id,
                UDINVerificationLog.tenant_id == tenant_id,
            )
            .order_by(UDINVerificationLog.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        udin_record_id: UUID | None = None,
        verified_by_id: UUID | None = None,
        result: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[UDINVerificationLog], int]:
        query = select(UDINVerificationLog).where(UDINVerificationLog.tenant_id == tenant_id)
        count_query = select(func.count(UDINVerificationLog.id)).where(UDINVerificationLog.tenant_id == tenant_id)

        if udin_record_id:
            query = query.where(UDINVerificationLog.udin_record_id == udin_record_id)
            count_query = count_query.where(UDINVerificationLog.udin_record_id == udin_record_id)

        if verified_by_id:
            query = query.where(UDINVerificationLog.verified_by_id == verified_by_id)
            count_query = count_query.where(UDINVerificationLog.verified_by_id == verified_by_id)

        if result:
            query = query.where(UDINVerificationLog.result == result)
            count_query = count_query.where(UDINVerificationLog.result == result)

        if date_from:
            query = query.where(UDINVerificationLog.created_at >= date_from)
            count_query = count_query.where(UDINVerificationLog.created_at >= date_from)

        if date_to:
            query = query.where(UDINVerificationLog.created_at <= date_to)
            count_query = count_query.where(UDINVerificationLog.created_at <= date_to)

        sort_column = getattr(UDINVerificationLog, sort_by, UDINVerificationLog.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(UDINVerificationLog.udin_record),
                selectinload(UDINVerificationLog.verified_by),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0