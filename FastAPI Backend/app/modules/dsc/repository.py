from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.dsc.models import DSCCertificate, DSCSigningLog, DSCRenewalRequest, DSCStatus


class DSCCertificateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, certificate: DSCCertificate) -> DSCCertificate:
        self.db.add(certificate)
        await self.db.flush()
        await self.db.refresh(certificate)
        return certificate

    async def get_by_id(self, certificate_id: UUID, tenant_id: UUID) -> DSCCertificate | None:
        result = await self.db.execute(
            select(DSCCertificate)
            .options(
                selectinload(DSCCertificate.holder),
                selectinload(DSCCertificate.custodian),
                selectinload(DSCCertificate.client),
            )
            .where(DSCCertificate.id == certificate_id, DSCCertificate.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_serial(self, serial_number: str, tenant_id: UUID) -> DSCCertificate | None:
        result = await self.db.execute(
            select(DSCCertificate).where(
                DSCCertificate.certificate_serial_number == serial_number,
                DSCCertificate.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_holder(self, holder_id: UUID, tenant_id: UUID) -> list[DSCCertificate]:
        result = await self.db.execute(
            select(DSCCertificate)
            .where(DSCCertificate.holder_id == holder_id, DSCCertificate.tenant_id == tenant_id)
            .order_by(DSCCertificate.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        holder_id: UUID | None = None,
        status: str | None = None,
        dsc_type: str | None = None,
        custodian_id: UUID | None = None,
        client_id: UUID | None = None,
        expiry_from: datetime | None = None,
        expiry_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[DSCCertificate], int]:
        query = select(DSCCertificate).where(DSCCertificate.tenant_id == tenant_id)
        count_query = select(func.count(DSCCertificate.id)).where(DSCCertificate.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    DSCCertificate.certificate_serial_number.ilike(search_term),
                    DSCCertificate.issuing_authority.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    DSCCertificate.certificate_serial_number.ilike(search_term),
                    DSCCertificate.issuing_authority.ilike(search_term),
                )
            )

        if holder_id:
            query = query.where(DSCCertificate.holder_id == holder_id)
            count_query = count_query.where(DSCCertificate.holder_id == holder_id)

        if status:
            query = query.where(DSCCertificate.status == status)
            count_query = count_query.where(DSCCertificate.status == status)

        if dsc_type:
            query = query.where(DSCCertificate.dsc_type == dsc_type)
            count_query = count_query.where(DSCCertificate.dsc_type == dsc_type)

        if custodian_id:
            query = query.where(DSCCertificate.custodian_id == custodian_id)
            count_query = count_query.where(DSCCertificate.custodian_id == custodian_id)

        if client_id:
            query = query.where(DSCCertificate.client_id == client_id)
            count_query = count_query.where(DSCCertificate.client_id == client_id)

        if expiry_from:
            query = query.where(DSCCertificate.expiry_date >= expiry_from)
            count_query = count_query.where(DSCCertificate.expiry_date >= expiry_from)

        if expiry_to:
            query = query.where(DSCCertificate.expiry_date <= expiry_to)
            count_query = count_query.where(DSCCertificate.expiry_date <= expiry_to)

        sort_column = getattr(DSCCertificate, sort_by, DSCCertificate.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(DSCCertificate.holder),
                selectinload(DSCCertificate.custodian),
                selectinload(DSCCertificate.client),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def get_expiring_soon(
        self, tenant_id: UUID, days: int = 30
    ) -> list[DSCCertificate]:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() + timedelta(days=days)
        result = await self.db.execute(
            select(DSCCertificate)
            .options(selectinload(DSCCertificate.holder))
            .where(
                DSCCertificate.tenant_id == tenant_id,
                DSCCertificate.status == DSCStatus.ACTIVE.value,
                DSCCertificate.expiry_date <= cutoff_date,
                DSCCertificate.expiry_date >= datetime.utcnow(),
            )
            .order_by(DSCCertificate.expiry_date.asc())
        )
        return list(result.scalars().all())

    async def update(self, certificate: DSCCertificate) -> DSCCertificate:
        await self.db.flush()
        await self.db.refresh(certificate)
        return certificate

    async def delete(self, certificate: DSCCertificate) -> None:
        await self.db.delete(certificate)
        await self.db.flush()


class DSCSigningLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: DSCSigningLog) -> DSCSigningLog:
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_by_id(self, log_id: UUID, tenant_id: UUID) -> DSCSigningLog | None:
        result = await self.db.execute(
            select(DSCSigningLog)
            .options(
                selectinload(DSCSigningLog.certificate),
                selectinload(DSCSigningLog.document),
                selectinload(DSCSigningLog.signed_by),
            )
            .where(DSCSigningLog.id == log_id, DSCSigningLog.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        certificate_id: UUID | None = None,
        document_id: UUID | None = None,
        signed_by_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[DSCSigningLog], int]:
        query = select(DSCSigningLog).where(DSCSigningLog.tenant_id == tenant_id)
        count_query = select(func.count(DSCSigningLog.id)).where(DSCSigningLog.tenant_id == tenant_id)

        if certificate_id:
            query = query.where(DSCSigningLog.certificate_id == certificate_id)
            count_query = count_query.where(DSCSigningLog.certificate_id == certificate_id)

        if document_id:
            query = query.where(DSCSigningLog.document_id == document_id)
            count_query = count_query.where(DSCSigningLog.document_id == document_id)

        if signed_by_id:
            query = query.where(DSCSigningLog.signed_by_id == signed_by_id)
            count_query = count_query.where(DSCSigningLog.signed_by_id == signed_by_id)

        if status:
            query = query.where(DSCSigningLog.status == status)
            count_query = count_query.where(DSCSigningLog.status == status)

        if date_from:
            query = query.where(DSCSigningLog.created_at >= date_from)
            count_query = count_query.where(DSCSigningLog.created_at >= date_from)

        if date_to:
            query = query.where(DSCSigningLog.created_at <= date_to)
            count_query = count_query.where(DSCSigningLog.created_at <= date_to)

        sort_column = getattr(DSCSigningLog, sort_by, DSCSigningLog.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(DSCSigningLog.certificate),
                selectinload(DSCSigningLog.document),
                selectinload(DSCSigningLog.signed_by),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, log: DSCSigningLog) -> DSCSigningLog:
        await self.db.flush()
        await self.db.refresh(log)
        return log


class DSCRenewalRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: DSCRenewalRequest) -> DSCRenewalRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> DSCRenewalRequest | None:
        result = await self.db.execute(
            select(DSCRenewalRequest)
            .options(
                selectinload(DSCRenewalRequest.certificate),
                selectinload(DSCRenewalRequest.requested_by),
                selectinload(DSCRenewalRequest.approved_by),
                selectinload(DSCRenewalRequest.rejected_by),
            )
            .where(DSCRenewalRequest.id == request_id, DSCRenewalRequest.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_certificate(self, certificate_id: UUID, tenant_id: UUID) -> list[DSCRenewalRequest]:
        result = await self.db.execute(
            select(DSCRenewalRequest)
            .where(
                DSCRenewalRequest.certificate_id == certificate_id,
                DSCRenewalRequest.tenant_id == tenant_id,
            )
            .order_by(DSCRenewalRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        certificate_id: UUID | None = None,
        requested_by_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[DSCRenewalRequest], int]:
        query = select(DSCRenewalRequest).where(DSCRenewalRequest.tenant_id == tenant_id)
        count_query = select(func.count(DSCRenewalRequest.id)).where(DSCRenewalRequest.tenant_id == tenant_id)

        if certificate_id:
            query = query.where(DSCRenewalRequest.certificate_id == certificate_id)
            count_query = count_query.where(DSCRenewalRequest.certificate_id == certificate_id)

        if requested_by_id:
            query = query.where(DSCRenewalRequest.requested_by_id == requested_by_id)
            count_query = count_query.where(DSCRenewalRequest.requested_by_id == requested_by_id)

        if status:
            query = query.where(DSCRenewalRequest.status == status)
            count_query = count_query.where(DSCRenewalRequest.status == status)

        if date_from:
            query = query.where(DSCRenewalRequest.created_at >= date_from)
            count_query = count_query.where(DSCRenewalRequest.created_at >= date_from)

        if date_to:
            query = query.where(DSCRenewalRequest.created_at <= date_to)
            count_query = count_query.where(DSCRenewalRequest.created_at <= date_to)

        sort_column = getattr(DSCRenewalRequest, sort_by, DSCRenewalRequest.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(DSCRenewalRequest.certificate),
                selectinload(DSCRenewalRequest.requested_by),
                selectinload(DSCRenewalRequest.approved_by),
                selectinload(DSCRenewalRequest.rejected_by),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, request: DSCRenewalRequest) -> DSCRenewalRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def delete(self, request: DSCRenewalRequest) -> None:
        await self.db.delete(request)
        await self.db.flush()