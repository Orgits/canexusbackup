from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.licenses.models import (
    License,
    LicenseDocument,
    LicenseRenewalRequest,
    LicenseStatus,
    LicenseType,
)
from app.modules.licenses.repository import (
    LicenseRepository,
    LicenseDocumentRepository,
    LicenseRenewalRequestRepository,
)
from app.modules.licenses.schemas import (
    LicenseCreate,
    LicenseUpdate,
    LicenseDocumentCreate,
    LicenseRenewalRequestCreate,
    LicenseRenewalRequestUpdate,
)
from app.modules.users.models import User
from app.modules.documents.models import Document


class LicenseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = LicenseRepository(db)

    async def create(self, data: LicenseCreate, tenant_id: UUID, created_by: UUID) -> License:
        # Validate professional
        professional_result = await self.db.execute(
            select(User).where(User.id == data.professional_id, User.tenant_id == tenant_id)
        )
        if not professional_result.scalar_one_or_none():
            raise NotFoundException(detail="Professional (user) not found")

        # Check for duplicate license number
        existing = await self.repository.get_by_number(data.license_number, tenant_id)
        if existing:
            raise ValidationException(detail="License with this number already exists")

        # Validate dates
        if data.expiry_date <= data.issue_date:
            raise ValidationException(detail="Expiry date must be after issue date")

        license = License(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=LicenseStatus.ACTIVE.value,
        )
        return await self.repository.create(license)

    async def get_by_id(self, license_id: UUID, tenant_id: UUID) -> License:
        license = await self.repository.get_by_id(license_id, tenant_id)
        if not license:
            raise NotFoundException(detail="License not found")
        return license

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
        return await self.repository.get_all(
            tenant_id, page, page_size, search, professional_id, status,
            license_type, expiry_from, expiry_to, sort_by, sort_order
        )

    async def update(self, license_id: UUID, tenant_id: UUID, data: LicenseUpdate, updated_by: UUID) -> License:
        license = await self.get_by_id(license_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            valid_transitions = {
                LicenseStatus.ACTIVE.value: [LicenseStatus.EXPIRED.value, LicenseStatus.PENDING_RENEWAL.value, LicenseStatus.SUSPENDED.value, LicenseStatus.REVOKED.value, LicenseStatus.SURRENDERED.value],
                LicenseStatus.PENDING_RENEWAL.value: [LicenseStatus.RENEWED.value, LicenseStatus.ACTIVE.value, LicenseStatus.EXPIRED.value, LicenseStatus.SUSPENDED.value, LicenseStatus.REVOKED.value],
                LicenseStatus.RENEWED.value: [LicenseStatus.ACTIVE.value, LicenseStatus.SUSPENDED.value, LicenseStatus.REVOKED.value],
                LicenseStatus.EXPIRED.value: [LicenseStatus.PENDING_RENEWAL.value, LicenseStatus.RENEWED.value, LicenseStatus.SURRENDERED.value],
                LicenseStatus.SUSPENDED.value: [LicenseStatus.ACTIVE.value, LicenseStatus.REVOKED.value, LicenseStatus.SURRENDERED.value],
                LicenseStatus.REVOKED.value: [],
                LicenseStatus.SURRENDERED.value: [],
            }
            current_status = license.status
            if new_status not in valid_transitions.get(current_status, []):
                raise ValidationException(detail=f"Invalid status transition from {current_status} to {new_status}")

            if new_status == LicenseStatus.SUSPENDED.value:
                license.suspended_at = datetime.utcnow()
                license.suspended_by_id = updated_by
                if "suspension_reason" in update_data:
                    license.suspension_reason = update_data.pop("suspension_reason")
            elif new_status == LicenseStatus.REVOKED.value:
                license.revoked_at = datetime.utcnow()
                license.revoked_by_id = updated_by
                if "revocation_reason" in update_data:
                    license.revocation_reason = update_data.pop("revocation_reason")
            elif new_status == LicenseStatus.RENEWED.value:
                license.renewed_at = datetime.utcnow()
                license.renewed_by_id = updated_by

        # Validate dates if updated
        if "expiry_date" in update_data or "issue_date" in update_data:
            new_expiry = update_data.get("expiry_date", license.expiry_date)
            new_issue = update_data.get("issue_date", license.issue_date)
            if new_expiry <= new_issue:
                raise ValidationException(detail="Expiry date must be after issue date")

        for field, value in update_data.items():
            setattr(license, field, value)

        license.updated_by = updated_by
        return await self.repository.update(license)

    async def suspend(self, license_id: UUID, tenant_id: UUID, suspended_by: UUID, reason: str) -> License:
        license = await self.get_by_id(license_id, tenant_id)
        if license.status not in [LicenseStatus.ACTIVE.value, LicenseStatus.RENEWED.value]:
            raise ValidationException(detail=f"Cannot suspend license with status: {license.status}")

        license.status = LicenseStatus.SUSPENDED.value
        license.suspended_at = datetime.utcnow()
        license.suspended_by_id = suspended_by
        license.suspension_reason = reason
        license.updated_by = suspended_by
        return await self.repository.update(license)

    async def revoke(self, license_id: UUID, tenant_id: UUID, revoked_by: UUID, reason: str) -> License:
        license = await self.get_by_id(license_id, tenant_id)
        if license.status == LicenseStatus.REVOKED.value:
            raise ValidationException(detail="License is already revoked")

        license.status = LicenseStatus.REVOKED.value
        license.revoked_at = datetime.utcnow()
        license.revoked_by_id = revoked_by
        license.revocation_reason = reason
        license.updated_by = revoked_by
        return await self.repository.update(license)

    async def get_expiring_soon(self, tenant_id: UUID, days: int = 30) -> list[License]:
        return await self.repository.get_expiring_soon(tenant_id, days)

    async def delete(self, license_id: UUID, tenant_id: UUID) -> None:
        license = await self.get_by_id(license_id, tenant_id)
        await self.repository.delete(license)


class LicenseDocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.license_repo = LicenseRepository(db)
        self.doc_repo = LicenseDocumentRepository(db)

    async def attach_document(self, data: LicenseDocumentCreate, tenant_id: UUID, uploaded_by: UUID) -> LicenseDocument:
        # Validate license
        license = await self.license_repo.get_by_id(data.license_id, tenant_id)
        if not license:
            raise NotFoundException(detail="License not found")

        # Validate document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == data.document_id, Document.tenant_id == tenant_id)
        )
        if not doc_result.scalar_one_or_none():
            raise NotFoundException(detail="Document not found")

        doc = LicenseDocument(
            license_id=data.license_id,
            document_id=data.document_id,
            document_type=data.document_type,
            description=data.description,
            uploaded_by_id=uploaded_by,
            uploaded_at=datetime.utcnow(),
            tenant_id=tenant_id,
            created_by=uploaded_by,
            extra_metadata=data.extra_metadata,
        )
        return await self.doc_repo.create(doc)

    async def get_documents(self, license_id: UUID, tenant_id: UUID) -> list[LicenseDocument]:
        return await self.doc_repo.get_by_license(license_id, tenant_id)

    async def detach_document(self, doc_id: UUID, tenant_id: UUID) -> None:
        doc = await self.doc_repo.get_by_id(doc_id, tenant_id)
        if not doc:
            raise NotFoundException(detail="License document not found")
        await self.doc_repo.delete(doc)


class LicenseRenewalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.license_repo = LicenseRepository(db)
        self.renewal_repo = LicenseRenewalRequestRepository(db)

    async def request_renewal(self, data: LicenseRenewalRequestCreate, tenant_id: UUID, requested_by: UUID) -> LicenseRenewalRequest:
        # Validate license
        license = await self.license_repo.get_by_id(data.license_id, tenant_id)
        if not license:
            raise NotFoundException(detail="License not found")

        if license.status not in [LicenseStatus.ACTIVE.value, LicenseStatus.EXPIRED.value, LicenseStatus.PENDING_RENEWAL.value]:
            raise ValidationException(detail=f"License cannot be renewed (status: {license.status})")

        # Check for existing pending renewal
        existing_requests = await self.renewal_repo.get_by_license(data.license_id, tenant_id)
        for req in existing_requests:
            if req.status == "pending":
                raise ValidationException(detail="A renewal request is already pending for this license")

        renewal = LicenseRenewalRequest(
            license_id=data.license_id,
            requested_by_id=requested_by,
            status="pending",
            new_expiry_date=data.new_expiry_date,
            application_number=data.application_number,
            application_date=data.application_date or datetime.utcnow(),
            fees_amount=data.fees_amount,
            tenant_id=tenant_id,
            created_by=requested_by,
            extra_metadata=data.extra_metadata,
        )

        # Update license status
        license.status = LicenseStatus.PENDING_RENEWAL.value
        license.renewal_application_date = datetime.utcnow()
        license.updated_by = requested_by
        await self.license_repo.update(license)

        return await self.renewal_repo.create(renewal)

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> LicenseRenewalRequest:
        renewal = await self.renewal_repo.get_by_id(request_id, tenant_id)
        if not renewal:
            raise NotFoundException(detail="Renewal request not found")
        return renewal

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
        return await self.renewal_repo.get_all(
            tenant_id, page, page_size, license_id, requested_by_id,
            status, date_from, date_to, sort_by, sort_order
        )

    async def approve(self, request_id: UUID, tenant_id: UUID, approved_by: UUID) -> LicenseRenewalRequest:
        renewal = await self.get_by_id(request_id, tenant_id)
        if renewal.status != "pending":
            raise ValidationException(detail="Only pending requests can be approved")

        renewal.status = "approved"
        renewal.approved_by_id = approved_by
        renewal.approved_at = datetime.utcnow()
        renewal.updated_by = approved_by

        # Update license
        license = await self.license_repo.get_by_id(renewal.license_id, tenant_id)
        if license:
            if renewal.new_expiry_date:
                license.expiry_date = renewal.new_expiry_date
            license.status = LicenseStatus.RENEWED.value
            license.renewed_at = datetime.utcnow()
            license.renewed_by_id = approved_by
            license.reminder_sent_at = None
            license.updated_by = approved_by
            await self.license_repo.update(license)

        return await self.renewal_repo.update(renewal)

    async def reject(self, request_id: UUID, tenant_id: UUID, rejected_by: UUID, reason: str) -> LicenseRenewalRequest:
        renewal = await self.get_by_id(request_id, tenant_id)
        if renewal.status != "pending":
            raise ValidationException(detail="Only pending requests can be rejected")

        renewal.status = "rejected"
        renewal.rejected_by_id = rejected_by
        renewal.rejected_at = datetime.utcnow()
        renewal.rejection_reason = reason
        renewal.updated_by = rejected_by

        # Revert license status
        license = await self.license_repo.get_by_id(renewal.license_id, tenant_id)
        if license:
            license.status = LicenseStatus.ACTIVE.value if license.expiry_date > datetime.utcnow() else LicenseStatus.EXPIRED.value
            license.updated_by = rejected_by
            await self.license_repo.update(license)

        return await self.renewal_repo.update(renewal)

    async def delete(self, request_id: UUID, tenant_id: UUID) -> None:
        renewal = await self.get_by_id(request_id, tenant_id)
        await self.renewal_repo.delete(renewal)