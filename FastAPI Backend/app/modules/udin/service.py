import hashlib
import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.udin.models import UDINRecord, UDINVerificationLog, UDINStatus
from app.modules.udin.repository import UDINRecordRepository, UDINVerificationLogRepository
from app.modules.udin.schemas import (
    UDINRecordCreate,
    UDINRecordUpdate,
    UDINGenerationRequest,
    UDINVerificationRequest,
)
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.matters.models import Matter
from app.modules.documents.models import Document


class UDINService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.record_repo = UDINRecordRepository(db)
        self.log_repo = UDINVerificationLogRepository(db)

    def _generate_udin(self) -> str:
        """Generate a UDIN - 18 digit alphanumeric code"""
        # UDIN format: YY + 16 alphanumeric characters
        # In production, this would integrate with ICAI's UDIN generation API
        year_suffix = datetime.utcnow().strftime("%y")
        random_part = secrets.token_hex(8).upper()[:16]
        return f"{year_suffix}{random_part}"

    async def generate_udin(self, data: UDINGenerationRequest, tenant_id: UUID, created_by: UUID) -> UDINRecord:
        # Validate professional
        professional_result = await self.db.execute(
            select(User).where(User.id == data.professional_id, User.tenant_id == tenant_id)
        )
        if not professional_result.scalar_one_or_none():
            raise NotFoundException(detail="Professional (user) not found")

        # Validate client if provided
        if data.client_id:
            client_result = await self.db.execute(
                select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        # Validate matter if provided
        if data.matter_id:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == data.matter_id, Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        # Validate document if provided
        if data.document_id:
            doc_result = await self.db.execute(
                select(Document).where(Document.id == data.document_id, Document.tenant_id == tenant_id)
            )
            if not doc_result.scalar_one_or_none():
                raise NotFoundException(detail="Document not found")

        # Generate unique UDIN
        max_attempts = 10
        for _ in range(max_attempts):
            udin = self._generate_udin()
            existing = await self.record_repo.get_by_udin(udin, tenant_id)
            if not existing:
                break
        else:
            raise ValidationException(detail="Failed to generate unique UDIN after multiple attempts")

        record = UDINRecord(
            udin=udin,
            professional_id=data.professional_id,
            financial_year=data.financial_year,
            quarter=data.quarter,
            form_type=data.form_type,
            client_id=data.client_id,
            matter_id=data.matter_id,
            document_id=data.document_id,
            description=data.description,
            external_reference=data.external_reference,
            generated_at=datetime.utcnow(),
            status=UDINStatus.GENERATED.value,
            tenant_id=tenant_id,
            created_by=created_by,
            extra_metadata=data.extra_metadata,
        )

        return await self.record_repo.create(record)

    async def get_by_id(self, record_id: UUID, tenant_id: UUID) -> UDINRecord:
        record = await self.record_repo.get_by_id(record_id, tenant_id)
        if not record:
            raise NotFoundException(detail="UDIN record not found")
        return record

    async def get_by_udin(self, udin: str, tenant_id: UUID) -> UDINRecord:
        record = await self.record_repo.get_by_udin(udin, tenant_id)
        if not record:
            raise NotFoundException(detail="UDIN record not found")
        return record

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
        return await self.record_repo.get_all(
            tenant_id, page, page_size, search, professional_id, status,
            client_id, matter_id, document_id, financial_year, quarter,
            form_type, date_from, date_to, sort_by, sort_order
        )

    async def update(self, record_id: UUID, tenant_id: UUID, data: UDINRecordUpdate, updated_by: UUID) -> UDINRecord:
        record = await self.get_by_id(record_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            valid_transitions = {
                UDINStatus.GENERATED.value: [UDINStatus.VERIFIED.value, UDINStatus.CANCELLED.value, UDINStatus.EXPIRED.value],
                UDINStatus.VERIFIED.value: [UDINStatus.CANCELLED.value],
                UDINStatus.CANCELLED.value: [],
                UDINStatus.EXPIRED.value: [],
            }
            current_status = record.status
            if new_status not in valid_transitions.get(current_status, []):
                raise ValidationException(detail=f"Invalid status transition from {current_status} to {new_status}")

            if new_status == UDINStatus.VERIFIED.value:
                record.verified_at = datetime.utcnow()
                record.verified_by_id = updated_by
            elif new_status == UDINStatus.CANCELLED.value:
                record.cancelled_at = datetime.utcnow()
                record.cancelled_by_id = updated_by
                if "cancellation_reason" in update_data:
                    record.cancellation_reason = update_data.pop("cancellation_reason")

        for field, value in update_data.items():
            setattr(record, field, value)

        record.updated_by = updated_by
        return await self.record_repo.update(record)

    async def verify_udin(self, data: UDINVerificationRequest, tenant_id: UUID, verified_by: UUID) -> UDINVerificationLog:
        # Find UDIN record
        record = await self.record_repo.get_by_udin(data.udin, tenant_id)
        if not record:
            # Log failed verification
            log = UDINVerificationLog(
                udin_record_id=None,  # Will be set if found
                verified_by_id=verified_by,
                result="not_found",
                verification_method=data.verification_method,
                external_response={"error": "UDIN not found in tenant records"},
                tenant_id=tenant_id,
                created_by=verified_by,
                extra_metadata=data.extra_metadata,
            )
            return await self.log_repo.create(log)

        # In production, this would call ICAI's UDIN verification API
        # For now, we simulate verification
        is_valid = record.status == UDINStatus.GENERATED.value
        result = "verified" if is_valid else "invalid_status"

        # Log verification attempt
        log = UDINVerificationLog(
            udin_record_id=record.id,
            verified_by_id=verified_by,
            result=result,
            verification_method=data.verification_method,
            external_response=data.extra_metadata.get("external_response"),
            tenant_id=tenant_id,
            created_by=verified_by,
            extra_metadata=data.extra_metadata,
        )

        if is_valid:
            record.status = UDINStatus.VERIFIED.value
            record.verified_at = datetime.utcnow()
            record.verified_by_id = verified_by
            record.updated_by = verified_by
            await self.record_repo.update(record)

        return await self.log_repo.create(log)

    async def cancel_udin(self, record_id: UUID, tenant_id: UUID, cancelled_by: UUID, reason: str) -> UDINRecord:
        record = await self.get_by_id(record_id, tenant_id)
        if record.status != UDINStatus.GENERATED.value:
            raise ValidationException(detail=f"Only generated UDINs can be cancelled (status: {record.status})")

        record.status = UDINStatus.CANCELLED.value
        record.cancelled_at = datetime.utcnow()
        record.cancelled_by_id = cancelled_by
        record.cancellation_reason = reason
        record.updated_by = cancelled_by
        return await self.record_repo.update(record)

    async def get_verification_logs(
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
        return await self.log_repo.get_all(
            tenant_id, page, page_size, udin_record_id, verified_by_id,
            result, date_from, date_to, sort_by, sort_order
        )

    async def delete(self, record_id: UUID, tenant_id: UUID) -> None:
        record = await self.get_by_id(record_id, tenant_id)
        await self.record_repo.delete(record)