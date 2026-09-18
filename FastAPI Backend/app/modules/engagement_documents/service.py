from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.engagement_documents.models import (
    EngagementDocument,
    EngagementDocumentSigner,
    EngagementDocumentVersion,
    EngagementDocumentTemplate,
    EngagementDocumentStatus,
    EngagementDocumentType,
)
from app.modules.engagement_documents.repository import (
    EngagementDocumentRepository,
    EngagementDocumentSignerRepository,
    EngagementDocumentVersionRepository,
    EngagementDocumentTemplateRepository,
)
from app.modules.engagement_documents.schemas import (
    EngagementDocumentCreate,
    EngagementDocumentUpdate,
    EngagementDocumentSignerCreate,
    EngagementDocumentSignerUpdate,
    EngagementDocumentVersionCreate,
    EngagementDocumentTemplateCreate,
    EngagementDocumentTemplateUpdate,
)
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.matters.models import Matter
from app.modules.templates.models import Template


class EngagementDocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = EngagementDocumentRepository(db)
        self.signer_repo = EngagementDocumentSignerRepository(db)
        self.version_repo = EngagementDocumentVersionRepository(db)
        self.template_repo = EngagementDocumentTemplateRepository(db)

    async def create(self, data: EngagementDocumentCreate, tenant_id: UUID, created_by: UUID) -> EngagementDocument:
        # Validate client
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

        # Validate engagement partner if provided
        if data.engagement_partner_id:
            partner_result = await self.db.execute(
                select(User).where(User.id == data.engagement_partner_id, User.tenant_id == tenant_id)
            )
            if not partner_result.scalar_one_or_none():
                raise NotFoundException(detail="Engagement partner not found")

        # Validate engagement manager if provided
        if data.engagement_manager_id:
            manager_result = await self.db.execute(
                select(User).where(User.id == data.engagement_manager_id, User.tenant_id == tenant_id)
            )
            if not manager_result.scalar_one_or_none():
                raise NotFoundException(detail="Engagement manager not found")

        # Validate template if provided
        if data.template_id:
            template_result = await self.db.execute(
                select(Template).where(Template.id == data.template_id, Template.tenant_id == tenant_id)
            )
            if not template_result.scalar_one_or_none():
                raise NotFoundException(detail="Template not found")

        # Check for duplicate document number
        existing = await self.repository.get_by_number(data.document_number, tenant_id)
        if existing:
            raise ValidationException(detail="Document with this number already exists")

        # Validate dates
        if data.valid_until and data.valid_from and data.valid_until <= data.valid_from:
            raise ValidationException(detail="Valid until date must be after valid from date")
        if data.period_end and data.period_start and data.period_end <= data.period_start:
            raise ValidationException(detail="Period end date must be after period start date")

        doc = EngagementDocument(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=EngagementDocumentStatus.DRAFT.value,
        )
        return await self.repository.create(doc)

    async def get_by_id(self, doc_id: UUID, tenant_id: UUID) -> EngagementDocument:
        doc = await self.repository.get_by_id(doc_id, tenant_id)
        if not doc:
            raise NotFoundException(detail="Engagement document not found")
        return doc

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
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, matter_id, status,
            document_type, engagement_partner_id, engagement_manager_id,
            date_from, date_to, sort_by, sort_order
        )

    async def update(self, doc_id: UUID, tenant_id: UUID, data: EngagementDocumentUpdate, updated_by: UUID) -> EngagementDocument:
        doc = await self.get_by_id(doc_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            valid_transitions = {
                EngagementDocumentStatus.DRAFT.value: [EngagementDocumentStatus.PENDING_REVIEW.value, EngagementDocumentStatus.PENDING_SIGNATURE.value, EngagementDocumentStatus.CANCELLED.value],
                EngagementDocumentStatus.PENDING_REVIEW.value: [EngagementDocumentStatus.DRAFT.value, EngagementDocumentStatus.PENDING_SIGNATURE.value, EngagementDocumentStatus.CANCELLED.value],
                EngagementDocumentStatus.PENDING_SIGNATURE.value: [EngagementDocumentStatus.PARTIALLY_SIGNED.value, EngagementDocumentStatus.FULLY_SIGNED.value, EngagementDocumentStatus.CANCELLED.value, EngagementDocumentStatus.EXPIRED.value],
                EngagementDocumentStatus.PARTIALLY_SIGNED.value: [EngagementDocumentStatus.FULLY_SIGNED.value, EngagementDocumentStatus.CANCELLED.value, EngagementDocumentStatus.EXPIRED.value],
                EngagementDocumentStatus.FULLY_SIGNED.value: [EngagementDocumentStatus.COMPLETED.value, EngagementDocumentStatus.EXPIRED.value],
                EngagementDocumentStatus.COMPLETED.value: [],
                EngagementDocumentStatus.EXPIRED.value: [],
                EngagementDocumentStatus.CANCELLED.value: [],
            }
            current_status = doc.status
            if new_status not in valid_transitions.get(current_status, []):
                raise ValidationException(detail=f"Invalid status transition from {current_status} to {new_status}")

            if new_status == EngagementDocumentStatus.FULLY_SIGNED.value:
                doc.signed_at = datetime.utcnow()
            elif new_status == EngagementDocumentStatus.COMPLETED.value:
                doc.completed_at = datetime.utcnow()

        # Validate dates
        if "valid_until" in update_data or "valid_from" in update_data:
            new_valid_until = update_data.get("valid_until", doc.valid_until)
            new_valid_from = update_data.get("valid_from", doc.valid_from)
            if new_valid_until and new_valid_from and new_valid_until <= new_valid_from:
                raise ValidationException(detail="Valid until date must be after valid from date")

        if "period_end" in update_data or "period_start" in update_data:
            new_period_end = update_data.get("period_end", doc.period_end)
            new_period_start = update_data.get("period_start", doc.period_start)
            if new_period_end and new_period_start and new_period_end <= new_period_start:
                raise ValidationException(detail="Period end date must be after period start date")

        for field, value in update_data.items():
            setattr(doc, field, value)

        doc.updated_by = updated_by
        return await self.repository.update(doc)

    async def create_version(self, doc_id: UUID, tenant_id: UUID, data: EngagementDocumentVersionCreate, created_by: UUID) -> EngagementDocumentVersion:
        doc = await self.get_by_id(doc_id, tenant_id)

        # Get latest version
        latest = await self.version_repo.get_latest_version(doc_id, tenant_id)
        new_version = (latest.version + 1) if latest else 1

        version = EngagementDocumentVersion(
            engagement_document_id=doc_id,
            version=new_version,
            document_content=data.document_content or doc.document_content,
            document_html=data.document_html or doc.document_html,
            variables=data.variables or doc.variables,
            created_by_id=created_by,
            change_summary=data.change_summary,
            tenant_id=tenant_id,
            created_by=created_by,
            extra_metadata=data.extra_metadata,
        )

        return await self.version_repo.create(version)

    async def get_versions(self, doc_id: UUID, tenant_id: UUID) -> list[EngagementDocumentVersion]:
        return await self.version_repo.get_by_document(doc_id, tenant_id)

    async def submit_for_signature(self, doc_id: UUID, tenant_id: UUID, signers_data: list[EngagementDocumentSignerCreate], submitted_by: UUID) -> EngagementDocument:
        doc = await self.get_by_id(doc_id, tenant_id)
        if doc.status not in [EngagementDocumentStatus.DRAFT.value, EngagementDocumentStatus.PENDING_REVIEW.value]:
            raise ValidationException(detail="Only draft or pending review documents can be submitted for signature")

        # Create signers
        for signer_data in signers_data:
            # Validate signer
            signer_result = await self.db.execute(
                select(User).where(User.id == signer_data.signer_id, User.tenant_id == tenant_id)
            )
            if not signer_result.scalar_one_or_none():
                raise NotFoundException(detail=f"Signer {signer_data.signer_id} not found")

            signer = EngagementDocumentSigner(
                engagement_document_id=doc_id,
                signer_id=signer_data.signer_id,
                signer_role=signer_data.signer_role,
                signing_order=signer_data.signing_order,
                status="pending",
                tenant_id=tenant_id,
                created_by=submitted_by,
                extra_metadata=signer_data.extra_metadata,
            )
            await self.signer_repo.create(signer)

        doc.status = EngagementDocumentStatus.PENDING_SIGNATURE.value
        doc.updated_by = submitted_by
        return await self.repository.update(doc)

    async def delete(self, doc_id: UUID, tenant_id: UUID) -> None:
        doc = await self.get_by_id(doc_id, tenant_id)
        await self.repository.delete(doc)


class EngagementDocumentSignerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = EngagementDocumentRepository(db)
        self.signer_repo = EngagementDocumentSignerRepository(db)

    async def get_signers(self, doc_id: UUID, tenant_id: UUID) -> list[EngagementDocumentSigner]:
        return await self.signer_repo.get_by_document(doc_id, tenant_id)

    async def update_signer(self, signer_id: UUID, tenant_id: UUID, data: EngagementDocumentSignerUpdate, updated_by: UUID) -> EngagementDocumentSigner:
        signer = await self.signer_repo.get_by_id(signer_id, tenant_id)
        if not signer:
            raise NotFoundException(detail="Signer not found")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(signer, field, value)

        signer.updated_by = updated_by
        return await self.signer_repo.update(signer)

    async def mark_signed(self, signer_id: UUID, tenant_id: UUID, signer: UUID, signature_data: dict) -> EngagementDocumentSigner:
        signer_record = await self.signer_repo.get_by_id(signer_id, tenant_id)
        if not signer_record:
            raise NotFoundException(detail="Signer not found")

        if signer_record.signer_id != signer:
            raise ValidationException(detail="Only the assigned signer can sign")

        if signer_record.status != "pending":
            raise ValidationException(detail="Signer has already signed or declined")

        signer_record.status = "signed"
        signer_record.signed_at = datetime.utcnow()
        signer_record.signature_data = signature_data
        signer_record.updated_by = signer

        # Check if all signers have signed
        doc = await self.doc_repo.get_by_id(signer_record.engagement_document_id, tenant_id)
        all_signers = await self.signer_repo.get_by_document(doc.id, tenant_id)
        all_signed = all(s.status == "signed" for s in all_signers)

        if all_signed:
            doc.status = EngagementDocumentStatus.FULLY_SIGNED.value
            doc.signed_at = datetime.utcnow()
        else:
            doc.status = EngagementDocumentStatus.PARTIALLY_SIGNED.value

        doc.updated_by = signer
        await self.doc_repo.update(doc)

        return await self.signer_repo.update(signer_record)

    async def decline(self, signer_id: UUID, tenant_id: UUID, signer: UUID, reason: str) -> EngagementDocumentSigner:
        signer_record = await self.signer_repo.get_by_id(signer_id, tenant_id)
        if not signer_record:
            raise NotFoundException(detail="Signer not found")

        if signer_record.signer_id != signer:
            raise ValidationException(detail="Only the assigned signer can decline")

        if signer_record.status != "pending":
            raise ValidationException(detail="Signer has already signed or declined")

        signer_record.status = "declined"
        signer_record.declined_at = datetime.utcnow()
        signer_record.decline_reason = reason
        signer_record.updated_by = signer

        # Update document status
        doc = await self.doc_repo.get_by_id(signer_record.engagement_document_id, tenant_id)
        doc.status = EngagementDocumentStatus.CANCELLED.value
        doc.updated_by = signer
        await self.doc_repo.update(doc)

        return await self.signer_repo.update(signer_record)

    async def send_reminder(self, signer_id: UUID, tenant_id: UUID, sent_by: UUID) -> EngagementDocumentSigner:
        signer_record = await self.signer_repo.get_by_id(signer_id, tenant_id)
        if not signer_record:
            raise NotFoundException(detail="Signer not found")

        signer_record.reminder_sent_at = datetime.utcnow()
        signer_record.reminder_count += 1
        signer_record.updated_by = sent_by
        return await self.signer_repo.update(signer_record)


class EngagementDocumentTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.template_repo = EngagementDocumentTemplateRepository(db)

    async def create(self, data: EngagementDocumentTemplateCreate, tenant_id: UUID, created_by: UUID) -> EngagementDocumentTemplate:
        # If setting as default, unset other defaults for this type
        if data.is_default:
            existing_default = await self.template_repo.get_default(data.document_type.value, tenant_id)
            if existing_default:
                existing_default.is_default = False
                await self.template_repo.update(existing_default)

        template = EngagementDocumentTemplate(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by_id=created_by,
            created_by=created_by,
        )
        return await self.template_repo.create(template)

    async def get_by_id(self, template_id: UUID, tenant_id: UUID) -> EngagementDocumentTemplate:
        template = await self.template_repo.get_by_id(template_id, tenant_id)
        if not template:
            raise NotFoundException(detail="Template not found")
        return template

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
        return await self.template_repo.get_all(
            tenant_id, page, page_size, document_type, is_active, search, sort_by, sort_order
        )

    async def get_by_type(self, document_type: str, tenant_id: UUID) -> list[EngagementDocumentTemplate]:
        return await self.template_repo.get_by_type(document_type, tenant_id)

    async def get_default(self, document_type: str, tenant_id: UUID) -> EngagementDocumentTemplate | None:
        return await self.template_repo.get_default(document_type, tenant_id)

    async def update(self, template_id: UUID, tenant_id: UUID, data: EngagementDocumentTemplateUpdate, updated_by: UUID) -> EngagementDocumentTemplate:
        template = await self.get_by_id(template_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle default flag
        if "is_default" in update_data and update_data["is_default"]:
            existing_default = await self.template_repo.get_default(template.document_type.value, tenant_id)
            if existing_default and existing_default.id != template_id:
                existing_default.is_default = False
                await self.template_repo.update(existing_default)

        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_by = updated_by
        return await self.template_repo.update(template)

    async def delete(self, template_id: UUID, tenant_id: UUID) -> None:
        template = await self.get_by_id(template_id, tenant_id)
        await self.template_repo.delete(template)