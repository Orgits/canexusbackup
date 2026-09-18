from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.licenses.models import License, LicenseDocument, LicenseRenewalRequest, LicenseStatus


class LicenseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, license: License) -> License:
        self.db.add(license)
        await self.db.flush()
        await self.db.refresh(license)
        return license

    async def get_by_id(self, license_id: UUID, tenant_id: UUID) -> License | None:
        result = await self.db.execute(
            select(License)
            .options(
                selectinload(License.professional),
                selectinload(License.renewed_by),
                selectinload(License.suspended_by),
                selectinload(License.revoked_by),
            )
            .where(License.id == license_id, License.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, license_number: str, tenant_id: UUID) -> License | None:
        result = await self.db.execute(
            select(License).where(
                License.license_number == license_number,
                License.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_professional(self, professional_id: UUID, tenant_id: UUID) -> list[License]:
        result = await self.db.execute(
            select(License)
            .where(License.professional_id == professional_id, License.tenant_id == tenant_id)
            .order_by(License.created_at.desc())
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
        license_type: str | None = None,
        expiry_from: datetime | None = None,
        expiry_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[License], int]:
        query = select(License).where(License.tenant_id == tenant_id)
        count_query = select(func.count(License.id)).where(License.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    License.license_number.ilike(search_term),
                    License.issuing_authority.ilike(search_term),
                    License.registration_number.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    License.license_number.ilike(search_term),
                    License.issuing_authority.ilike(search_term),
                    License.registration_number.ilike(search_term),
                )
            )

        if professional_id:
            query = query.where(License.professional_id == professional_id)
            count_query = count_query.where(License.professional_id == professional_id)

        if status:
            query = query.where(License.status == status)
            count_query = count_query.where(License.status == status)

        if license_type:
            query = query.where(License.license_type == license_type)
            count_query = count_query.where(License.license_type == license_type)

        if expiry_from:
            query = query.where(License.expiry_date >= expiry_from)
            count_query = count_query.where(License.expiry_date >= expiry_from)

        if expiry_to:
            query = query.where(License.expiry_date <= expiry_to)
            count_query = count_query.where(License.expiry_date <= expiry_to)

        sort_column = getattr(License, sort_by, License.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(License.professional),
                selectinload(License.renewed_by),
                selectinload(License.suspended_by),
                selectinload(License.revoked_by),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def get_expiring_soon(
        self, tenant_id: UUID, days: int = 30
    ) -> list[License]:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() + timedelta(days=days)
        result = await self.db.execute(
            select(License)
            .options(selectinload(License.professional))
            .where(
                License.tenant_id == tenant_id,
                License.status.in_([LicenseStatus.ACTIVE.value, LicenseStatus.PENDING_RENEWAL.value]),
                License.expiry_date <= cutoff_date,
                License.expiry_date >= datetime.utcnow(),
            )
            .order_by(License.expiry_date.asc())
        )
        return list(result.scalars().all())

    async def update(self, license: License) -> License:
        await self.db.flush()
        await self.db.refresh(license)
        return license

    async def delete(self, license: License) -> None:
        await self.db.delete(license)
        await self.db.flush()


class LicenseDocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, doc: LicenseDocument) -> LicenseDocument:
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: UUID, tenant_id: UUID) -> LicenseDocument | None:
        result = await self.db.execute(
            select(LicenseDocument)
            .options(
                selectinload(LicenseDocument.license),
                selectinload(LicenseDocument.document),
                selectinload(LicenseDocument.uploaded_by),
            )
            .where(LicenseDocument.id == doc_id, LicenseDocument.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_license(self, license_id: UUID, tenant_id: UUID) -> list[LicenseDocument]:
        result = await self.db.execute(
            select(LicenseDocument)
            .options(selectinload(LicenseDocument.document))
            .where(LicenseDocument.license_id == license_id, LicenseDocument.tenant_id == tenant_id)
            .order_by(LicenseDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        license_id: UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[LicenseDocument], int]:
        query = select(LicenseDocument).where(LicenseDocument.tenant_id == tenant_id)
        count_query = select(func.count(LicenseDocument.id)).where(LicenseDocument.tenant_id == tenant_id)

        if license_id:
            query = query.where(LicenseDocument.license_id == license_id)
            count_query = count_query.where(LicenseDocument.license_id == license_id)

        sort_column = getattr(LicenseDocument, sort_by, LicenseDocument.uploaded_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(LicenseDocument.license),
                selectinload(LicenseDocument.document),
                selectinload(LicenseDocument.uploaded_by),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def delete(self, doc: LicenseDocument) -> None:
        await self.db.delete(doc)
        await self.db.flush()


class LicenseRenewalRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: LicenseRenewalRequest) -> LicenseRenewalRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> LicenseRenewalRequest | None:
        result = await self.db.execute(
            select(LicenseRenewalRequest)
            .options(
                selectinload(LicenseRenewalRequest.license),
                selectinload(LicenseRenewalRequest.requested_by),
                selectinload(LicenseRenewalRequest.approved_by),
                selectinload(LicenseRenewalRequest.rejected_by),
            )
            .where(LicenseRenewalRequest.id == request_id, LicenseRenewalRequest.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_license(self, license_id: UUID, tenant_id: UUID) -> list[LicenseRenewalRequest]:
        result = await self.db.execute(
            select(LicenseRenewalRequest)
            .where(
                LicenseRenewalRequest.license_id == license_id,
                LicenseRenewalRequest.tenant_id == tenant_id,
            )
            .order_by(LicenseRenewalRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        license_id: UUID | None = None,
        requested_by_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[LicenseRenewalRequest], int]:
        query = select(LicenseRenewalRequest).where(LicenseRenewalRequest.tenant_id == tenant_id)
        count_query = select(func.count(LicenseRenewalRequest.id)).where(LicenseRenewalRequest.tenant_id == tenant_id)

        if license_id:
            query = query.where(LicenseRenewalRequest.license_id == license_id)
            count_query = count_query.where(LicenseRenewalRequest.license_id == license_id)

        if requested_by_id:
            query = query.where(LicenseRenewalRequest.requested_by_id == requested_by_id)
            count_query = count_query.where(LicenseRenewalRequest.requested_by_id == requested_by_id)

        if status:
            query = query.where(LicenseRenewalRequest.status == status)
            count_query = count_query.where(LicenseRenewalRequest.status == status)

        if date_from:
            query = query.where(LicenseRenewalRequest.created_at >= date_from)
            count_query = count_query.where(LicenseRenewalRequest.created_at >= date_from)

        if date_to:
            query = query.where(LicenseRenewalRequest.created_at <= date_to)
            count_query = count_query.where(LicenseRenewalRequest.created_at <= date_to)

        sort_column = getattr(LicenseRenewalRequest, sort_by, LicenseRenewalRequest.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(LicenseRenewalRequest.license),
                selectinload(LicenseRenewalRequest.requested_by),
                selectinload(LicenseRenewalRequest.approved_by),
                selectinload(LicenseRenewalRequest.rejected_by),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, request: LicenseRenewalRequest) -> LicenseRenewalRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def delete(self, request: LicenseRenewalRequest) -> None:
        await self.db.delete(request)
        await self.db.flush()