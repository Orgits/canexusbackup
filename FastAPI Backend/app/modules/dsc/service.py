from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.security.encryption import encrypt_field, decrypt_field
from app.modules.dsc.models import (
    DSCCertificate,
    DSCSigningLog,
    DSCRenewalRequest,
    DSCStatus,
    DSCType,
)
from app.modules.dsc.repository import (
    DSCCertificateRepository,
    DSCSigningLogRepository,
    DSCRenewalRequestRepository,
)
from app.modules.dsc.schemas import (
    DSCCertificateCreate,
    DSCCertificateUpdate,
    DSCCertificateSignRequest,
    DSCSigningLogCreate,
    DSCRenewalRequestCreate,
    DSCRenewalRequestUpdate,
)
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.documents.models import Document


class DSCCertificateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DSCCertificateRepository(db)

    async def create(self, data: DSCCertificateCreate, tenant_id: UUID, created_by: UUID) -> DSCCertificate:
        # Validate holder exists
        holder_result = await self.db.execute(
            select(User).where(User.id == data.holder_id, User.tenant_id == tenant_id)
        )
        if not holder_result.scalar_one_or_none():
            raise NotFoundException(detail="Holder (user) not found")

        # Validate custodian if provided
        if data.custodian_id:
            custodian_result = await self.db.execute(
                select(User).where(User.id == data.custodian_id, User.tenant_id == tenant_id)
            )
            if not custodian_result.scalar_one_or_none():
                raise NotFoundException(detail="Custodian not found")

        # Validate client if provided
        if data.client_id:
            client_result = await self.db.execute(
                select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        # Check for duplicate serial number
        existing = await self.repository.get_by_serial(data.certificate_serial_number, tenant_id)
        if existing:
            raise ValidationException(detail="Certificate with this serial number already exists")

        # Validate dates
        if data.expiry_date <= data.issue_date:
            raise ValidationException(detail="Expiry date must be after issue date")

        certificate = DSCCertificate(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=DSCStatus.ACTIVE.value,
        )
        return await self.repository.create(certificate)

    async def get_by_id(self, certificate_id: UUID, tenant_id: UUID) -> DSCCertificate:
        certificate = await self.repository.get_by_id(certificate_id, tenant_id)
        if not certificate:
            raise NotFoundException(detail="DSC certificate not found")
        return certificate

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
        return await self.repository.get_all(
            tenant_id, page, page_size, search, holder_id, status, dsc_type,
            custodian_id, client_id, expiry_from, expiry_to, sort_by, sort_order
        )

    async def update(self, certificate_id: UUID, tenant_id: UUID, data: DSCCertificateUpdate, updated_by: UUID) -> DSCCertificate:
        certificate = await self.get_by_id(certificate_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            valid_transitions = {
                DSCStatus.ACTIVE.value: [DSCStatus.EXPIRED.value, DSCStatus.REVOKED.value, DSCStatus.PENDING_RENEWAL.value],
                DSCStatus.PENDING_RENEWAL.value: [DSCStatus.RENEWED.value, DSCStatus.ACTIVE.value, DSCStatus.EXPIRED.value],
                DSCStatus.RENEWED.value: [DSCStatus.ACTIVE.value],
                DSCStatus.EXPIRED.value: [DSCStatus.RENEWED.value, DSCStatus.PENDING_RENEWAL.value],
                DSCStatus.REVOKED.value: [],
            }
            current_status = certificate.status
            if new_status not in valid_transitions.get(current_status, []):
                raise ValidationException(detail=f"Invalid status transition from {current_status} to {new_status}")

            if new_status == DSCStatus.REVOKED.value:
                certificate.revoked_at = datetime.utcnow()
                certificate.revoked_by = updated_by
                if "revocation_reason" in update_data:
                    certificate.revocation_reason = update_data.pop("revocation_reason")

        # Validate dates if updated
        if "expiry_date" in update_data or "issue_date" in update_data:
            new_expiry = update_data.get("expiry_date", certificate.expiry_date)
            new_issue = update_data.get("issue_date", certificate.issue_date)
            if new_expiry <= new_issue:
                raise ValidationException(detail="Expiry date must be after issue date")

        for field, value in update_data.items():
            setattr(certificate, field, value)

        certificate.updated_by = updated_by
        return await self.repository.update(certificate)

    async def revoke(self, certificate_id: UUID, tenant_id: UUID, revoked_by: UUID, reason: str | None = None) -> DSCCertificate:
        certificate = await self.get_by_id(certificate_id, tenant_id)
        if certificate.status == DSCStatus.REVOKED.value:
            raise ValidationException(detail="Certificate is already revoked")

        certificate.status = DSCStatus.REVOKED.value
        certificate.revoked_at = datetime.utcnow()
        certificate.revoked_by = revoked_by
        certificate.revocation_reason = reason
        certificate.updated_by = revoked_by
        return await self.repository.update(certificate)

    async def get_expiring_soon(self, tenant_id: UUID, days: int = 30) -> list[DSCCertificate]:
        return await self.repository.get_expiring_soon(tenant_id, days)

    async def delete(self, certificate_id: UUID, tenant_id: UUID) -> None:
        certificate = await self.get_by_id(certificate_id, tenant_id)
        await self.repository.delete(certificate)

    async def store_certificate_data(
        self,
        certificate_id: UUID,
        tenant_id: UUID,
        certificate_pem: bytes,
        private_key: bytes,
        passphrase: str | None = None,
        updated_by: UUID | None = None,
    ) -> DSCCertificate:
        certificate = await self.get_by_id(certificate_id, tenant_id)

        certificate.certificate_pem = certificate_pem
        certificate.private_key_encrypted = encrypt_field(private_key)
        if passphrase:
            certificate.passphrase_hash = passphrase  # Should be hashed in production
        certificate.updated_by = updated_by

        return await self.repository.update(certificate)

    async def get_private_key(self, certificate_id: UUID, tenant_id: UUID, passphrase: str | None = None) -> bytes | None:
        certificate = await self.get_by_id(certificate_id, tenant_id)
        if not certificate.private_key_encrypted:
            return None

        # In production, verify passphrase against hash
        if certificate.passphrase_hash and passphrase != certificate.passphrase_hash:
            raise ValidationException(detail="Invalid passphrase")

        return decrypt_field(certificate.private_key_encrypted)


class DSCSigningService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.certificate_repo = DSCCertificateRepository(db)
        self.log_repo = DSCSigningLogRepository(db)

    async def sign_document(
        self,
        data: DSCCertificateSignRequest,
        tenant_id: UUID,
        signed_by_id: UUID,
        request_id: str | None = None,
    ) -> DSCSigningLog:
        # Validate certificate
        certificate = await self.certificate_repo.get_by_id(data.certificate_id, tenant_id)
        if not certificate:
            raise NotFoundException(detail="DSC certificate not found")

        if certificate.status != DSCStatus.ACTIVE.value:
            raise ValidationException(detail=f"Certificate is not active (status: {certificate.status})")

        if certificate.expiry_date < datetime.utcnow():
            raise ValidationException(detail="Certificate has expired")

        # Validate document if provided
        if data.document_id:
            doc_result = await self.db.execute(
                select(Document).where(Document.id == data.document_id, Document.tenant_id == tenant_id)
            )
            if not doc_result.scalar_one_or_none():
                raise NotFoundException(detail="Document not found")

        # In production, this would call external DSC provider or use local signing
        # For now, we log the signing attempt
        import hashlib
        signature_hash = hashlib.sha256(f"{data.document_id}{datetime.utcnow().isoformat()}".encode()).hexdigest()

        log = DSCSigningLog(
            certificate_id=data.certificate_id,
            document_id=data.document_id,
            signed_by_id=signed_by_id,
            signing_purpose=data.signing_purpose,
            signature_algorithm=data.signature_algorithm,
            signature_hash=signature_hash,
            status="success",
            ip_address=None,  # Would be set from request context
            user_agent=None,
            request_id=request_id,
            tenant_id=tenant_id,
            created_by=signed_by_id,
        )

        return await self.log_repo.create(log)

    async def get_signing_logs(
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
        return await self.log_repo.get_all(
            tenant_id, page, page_size, certificate_id, document_id,
            signed_by_id, status, date_from, date_to, sort_by, sort_order
        )


class DSCRenewalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.certificate_repo = DSCCertificateRepository(db)
        self.renewal_repo = DSCRenewalRequestRepository(db)

    async def request_renewal(self, data: DSCRenewalRequestCreate, tenant_id: UUID, requested_by: UUID) -> DSCRenewalRequest:
        # Validate certificate
        certificate = await self.certificate_repo.get_by_id(data.certificate_id, tenant_id)
        if not certificate:
            raise NotFoundException(detail="DSC certificate not found")

        if certificate.status not in [DSCStatus.ACTIVE.value, DSCStatus.EXPIRED.value, DSCStatus.PENDING_RENEWAL.value]:
            raise ValidationException(detail=f"Certificate cannot be renewed (status: {certificate.status})")

        # Check for existing pending renewal
        existing_requests = await self.renewal_repo.get_by_certificate(data.certificate_id, tenant_id)
        for req in existing_requests:
            if req.status == "pending":
                raise ValidationException(detail="A renewal request is already pending for this certificate")

        renewal = DSCRenewalRequest(
            **data.model_dump(),
            tenant_id=tenant_id,
            requested_by_id=requested_by,
            status="pending",
            created_by=requested_by,
        )

        # Update certificate status
        certificate.status = DSCStatus.PENDING_RENEWAL.value
        certificate.renewal_initiated_at = datetime.utcnow()
        certificate.updated_by = requested_by
        await self.certificate_repo.update(certificate)

        return await self.renewal_repo.create(renewal)

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> DSCRenewalRequest:
        renewal = await self.renewal_repo.get_by_id(request_id, tenant_id)
        if not renewal:
            raise NotFoundException(detail="Renewal request not found")
        return renewal

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
        return await self.renewal_repo.get_all(
            tenant_id, page, page_size, certificate_id, requested_by_id,
            status, date_from, date_to, sort_by, sort_order
        )

    async def approve(self, request_id: UUID, tenant_id: UUID, approved_by: UUID) -> DSCRenewalRequest:
        renewal = await self.get_by_id(request_id, tenant_id)
        if renewal.status != "pending":
            raise ValidationException(detail="Only pending requests can be approved")

        renewal.status = "approved"
        renewal.approved_by_id = approved_by
        renewal.approved_at = datetime.utcnow()
        renewal.updated_by = approved_by

        # Update certificate
        certificate = await self.certificate_repo.get_by_id(renewal.certificate_id, tenant_id)
        if certificate:
            if renewal.new_expiry_date:
                certificate.expiry_date = renewal.new_expiry_date
            certificate.status = DSCStatus.RENEWED.value
            certificate.renewal_reminder_sent = False
            certificate.updated_by = approved_by
            await self.certificate_repo.update(certificate)

        return await self.renewal_repo.update(renewal)

    async def reject(self, request_id: UUID, tenant_id: UUID, rejected_by: UUID, reason: str) -> DSCRenewalRequest:
        renewal = await self.get_by_id(request_id, tenant_id)
        if renewal.status != "pending":
            raise ValidationException(detail="Only pending requests can be rejected")

        renewal.status = "rejected"
        renewal.rejected_by_id = rejected_by
        renewal.rejected_at = datetime.utcnow()
        renewal.rejection_reason = reason
        renewal.updated_by = rejected_by

        # Revert certificate status
        certificate = await self.certificate_repo.get_by_id(renewal.certificate_id, tenant_id)
        if certificate:
            certificate.status = DSCStatus.ACTIVE.value if certificate.expiry_date > datetime.utcnow() else DSCStatus.EXPIRED.value
            certificate.updated_by = rejected_by
            await self.certificate_repo.update(certificate)

        return await self.renewal_repo.update(renewal)

    async def delete(self, request_id: UUID, tenant_id: UUID) -> None:
        renewal = await self.get_by_id(request_id, tenant_id)
        await self.renewal_repo.delete(renewal)