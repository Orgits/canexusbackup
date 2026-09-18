from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.dpdp.models import (
    DataAccessRequest,
    DataCorrectionRequest,
    DataErasureRequest,
    RetentionPolicy,
    RetentionExecution,
    DataResidencyRecord,
    DataAccessStatus,
    DataCorrectionStatus,
    DataErasureStatus,
    RetentionAction,
)
from app.modules.dpdp.repository import DPDPRepository
from app.modules.dpdp.schemas import (
    DataAccessRequestCreate,
    DataAccessRequestUpdate,
    DataCorrectionRequestCreate,
    DataCorrectionRequestUpdate,
    DataErasureRequestCreate,
    DataErasureRequestUpdate,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
    DataResidencyRecordCreate,
    DataResidencyRecordUpdate,
)


class DPDPService:
    def __init__(self, db: AsyncSession, tenant_id: UUID, user_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repository = DPDPRepository(db, tenant_id)

    # Data Access Requests
    async def create_data_access_request(self, data: DataAccessRequestCreate) -> DataAccessRequest:
        request = DataAccessRequest(
            subject_id=data.subject_id,
            client_id=data.client_id,
            scope=data.scope,
            legal_basis=data.legal_basis,
            status=DataAccessStatus.PENDING,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_data_access_request(request)

    async def get_data_access_request(self, request_id: UUID) -> DataAccessRequest:
        request = await self.repository.get_data_access_request(request_id)
        if not request:
            raise NotFoundException("Data access request not found")
        return request

    async def list_data_access_requests(
        self,
        subject_id: Optional[UUID] = None,
        client_id: Optional[UUID] = None,
        status: Optional[DataAccessStatus] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[DataAccessRequest], int]:
        return await self.repository.list_data_access_requests(
            subject_id=subject_id,
            client_id=client_id,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_data_access_request(self, request_id: UUID, data: DataAccessRequestUpdate) -> DataAccessRequest:
        request = await self.get_data_access_request(request_id)

        if data.status is not None:
            request.status = data.status
            if data.status == DataAccessStatus.APPROVED:
                request.approved_by_id = self.user_id
                request.approved_at = datetime.utcnow()
            elif data.status == DataAccessStatus.REJECTED:
                request.approved_by_id = self.user_id
                request.approved_at = datetime.utcnow()
                request.rejection_reason = data.rejection_reason

        if data.rejection_reason is not None:
            request.rejection_reason = data.rejection_reason
        if data.compiled_data_ref is not None:
            request.compiled_data_ref = data.compiled_data_ref
        if data.compiled_size is not None:
            request.compiled_size = data.compiled_size
        if data.compiled_checksum is not None:
            request.compiled_checksum = data.compiled_checksum
        if data.expires_at is not None:
            request.expires_at = data.expires_at
        if data.error_message is not None:
            request.error_message = data.error_message

        return await self.repository.update_data_access_request(request)

    async def approve_data_access_request(self, request_id: UUID) -> DataAccessRequest:
        return await self.update_data_access_request(request_id, DataAccessRequestUpdate(status=DataAccessStatus.APPROVED))

    async def reject_data_access_request(self, request_id: UUID, reason: str) -> DataAccessRequest:
        return await self.update_data_access_request(request_id, DataAccessRequestUpdate(status=DataAccessStatus.REJECTED, rejection_reason=reason))

    # Data Correction Requests
    async def create_data_correction_request(self, data: DataCorrectionRequestCreate) -> DataCorrectionRequest:
        request = DataCorrectionRequest(
            subject_id=data.subject_id,
            client_id=data.client_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            field_name=data.field_name,
            old_value=data.old_value,
            new_value=data.new_value,
            justification=data.justification,
            status=DataCorrectionStatus.PENDING,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_data_correction_request(request)

    async def get_data_correction_request(self, request_id: UUID) -> DataCorrectionRequest:
        request = await self.repository.get_data_correction_request(request_id)
        if not request:
            raise NotFoundException("Data correction request not found")
        return request

    async def list_data_correction_requests(
        self,
        subject_id: Optional[UUID] = None,
        client_id: Optional[UUID] = None,
        entity_type: Optional[str] = None,
        status: Optional[DataCorrectionStatus] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[DataCorrectionRequest], int]:
        return await self.repository.list_data_correction_requests(
            subject_id=subject_id,
            client_id=client_id,
            entity_type=entity_type,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_data_correction_request(self, request_id: UUID, data: DataCorrectionRequestUpdate) -> DataCorrectionRequest:
        request = await self.get_data_correction_request(request_id)

        if data.status is not None:
            request.status = data.status
            if data.status == DataCorrectionStatus.UNDER_REVIEW:
                request.reviewed_by_id = self.user_id
                request.reviewed_at = datetime.utcnow()
            elif data.status == DataCorrectionStatus.APPROVED:
                request.reviewed_by_id = self.user_id
                request.reviewed_at = datetime.utcnow()
            elif data.status == DataCorrectionStatus.REJECTED:
                request.reviewed_by_id = self.user_id
                request.reviewed_at = datetime.utcnow()

        if data.review_notes is not None:
            request.review_notes = data.review_notes
        if data.error_message is not None:
            request.error_message = data.error_message

        return await self.repository.update_data_correction_request(request)

    async def approve_data_correction_request(self, request_id: UUID, review_notes: Optional[str] = None) -> DataCorrectionRequest:
        return await self.update_data_correction_request(request_id, DataCorrectionRequestUpdate(status=DataCorrectionStatus.APPROVED, review_notes=review_notes))

    async def reject_data_correction_request(self, request_id: UUID, review_notes: str) -> DataCorrectionRequest:
        return await self.update_data_correction_request(request_id, DataCorrectionRequestUpdate(status=DataCorrectionStatus.REJECTED, review_notes=review_notes))

    async def apply_data_correction(self, request_id: UUID) -> DataCorrectionRequest:
        request = await self.get_data_correction_request(request_id)
        
        if request.status != DataCorrectionStatus.APPROVED:
            raise ValidationException("Can only apply approved correction requests")

        from app.modules.clients.models import Client
        from app.modules.matters.models import Matter
        from app.modules.tasks.models import Task
        from app.modules.documents.models import Document
        from app.modules.billing.models import Invoice, Payment, Expense
        from sqlalchemy import select

        model_map = {
            "Client": Client,
            "Matter": Matter,
            "Task": Task,
            "Document": Document,
            "Invoice": Invoice,
            "Payment": Payment,
            "Expense": Expense,
        }

        if request.entity_type not in model_map:
            raise ValidationException(f"Unsupported entity type: {request.entity_type}")

        Model = model_map[request.entity_type]

        query = select(Model).where(
            and_(
                Model.id == request.entity_id,
                Model.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(query)
        entity = result.scalar_one_or_none()

        if not entity:
            raise NotFoundException(f"Entity {request.entity_type} not found")

        if not hasattr(entity, request.field_name):
            raise ValidationException(f"Field {request.field_name} not found on {request.entity_type}")

        old_value = getattr(entity, request.field_name)
        setattr(entity, request.field_name, request.new_value)

        request.status = DataCorrectionStatus.APPLIED
        request.applied_at = datetime.utcnow()
        request.applied_by_id = self.user_id

        await self.repository.update_data_correction_request(request)

        from app.modules.outbox.service import OutboxService
        from app.modules.outbox.models import OutboxEventType
        outbox_service = OutboxService(self.db)
        await outbox_service.create_event(
            event_type=OutboxEventType.DATA_CORRECTION_APPLIED,
            aggregate_type=request.entity_type.lower(),
            aggregate_id=request.entity_id,
            payload={
                "correction_request_id": str(request.id),
                "entity_type": request.entity_type,
                "entity_id": str(request.entity_id),
                "field_name": request.field_name,
                "old_value": str(old_value) if old_value else None,
                "new_value": request.new_value,
            },
            tenant_id=self.tenant_id,
        )

        return request

    # Data Erasure Requests
    async def create_data_erasure_request(self, data: DataErasureRequestCreate) -> DataErasureRequest:
        request = DataErasureRequest(
            subject_id=data.subject_id,
            client_id=data.client_id,
            scope=data.scope,
            legal_basis=data.legal_basis,
            external_refs=data.external_refs,
            status=DataErasureStatus.PENDING,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_data_erasure_request(request)

    async def get_data_erasure_request(self, request_id: UUID) -> DataErasureRequest:
        request = await self.repository.get_data_erasure_request(request_id)
        if not request:
            raise NotFoundException("Data erasure request not found")
        return request

    async def list_data_erasure_requests(
        self,
        subject_id: Optional[UUID] = None,
        client_id: Optional[UUID] = None,
        status: Optional[DataErasureStatus] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[DataErasureRequest], int]:
        return await self.repository.list_data_erasure_requests(
            subject_id=subject_id,
            client_id=client_id,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_data_erasure_request(self, request_id: UUID, data: DataErasureRequestUpdate) -> DataErasureRequest:
        request = await self.get_data_erasure_request(request_id)

        if data.status is not None:
            request.status = data.status
            if data.status == DataErasureStatus.APPROVED:
                request.approved_by_id = self.user_id
                request.approved_at = datetime.utcnow()
            elif data.status == DataErasureStatus.REJECTED:
                request.approved_by_id = self.user_id
                request.approved_at = datetime.utcnow()
                request.rejection_reason = data.rejection_reason

        if data.rejection_reason is not None:
            request.rejection_reason = data.rejection_reason
        if data.error_message is not None:
            request.error_message = data.error_message
        if data.error_details is not None:
            request.error_details = data.error_details
        if data.verification_token is not None:
            request.verification_token = data.verification_token
        if data.verified_at is not None:
            request.verified_at = data.verified_at

        return await self.repository.update_data_erasure_request(request)

    async def approve_data_erasure_request(self, request_id: UUID) -> DataErasureRequest:
        return await self.update_data_erasure_request(request_id, DataErasureRequestUpdate(status=DataErasureStatus.APPROVED))

    async def reject_data_erasure_request(self, request_id: UUID, reason: str) -> DataErasureRequest:
        return await self.update_data_erasure_request(request_id, DataErasureRequestUpdate(status=DataErasureStatus.REJECTED, rejection_reason=reason))

    # Retention Policies
    async def create_retention_policy(self, data: RetentionPolicyCreate) -> RetentionPolicy:
        policy = RetentionPolicy(
            name=data.name,
            description=data.description,
            entity_type=data.entity_type,
            criteria=data.criteria,
            retention_days=data.retention_days,
            action=data.action,
            protected=data.protected,
            protection_reason=data.protection_reason,
            is_active=data.is_active,
            created_by_id=self.user_id,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_retention_policy(policy)

    async def get_retention_policy(self, policy_id: UUID) -> RetentionPolicy:
        policy = await self.repository.get_retention_policy(policy_id)
        if not policy:
            raise NotFoundException("Retention policy not found")
        return policy

    async def list_retention_policies(
        self,
        entity_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[RetentionPolicy], int]:
        return await self.repository.list_retention_policies(
            entity_type=entity_type,
            is_active=is_active,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_retention_policy(self, policy_id: UUID, data: RetentionPolicyUpdate) -> RetentionPolicy:
        policy = await self.get_retention_policy(policy_id)

        if data.name is not None:
            policy.name = data.name
        if data.description is not None:
            policy.description = data.description
        if data.entity_type is not None:
            policy.entity_type = data.entity_type
        if data.criteria is not None:
            policy.criteria = data.criteria
        if data.retention_days is not None:
            policy.retention_days = data.retention_days
        if data.action is not None:
            policy.action = data.action
        if data.protected is not None:
            policy.protected = data.protected
        if data.protection_reason is not None:
            policy.protection_reason = data.protection_reason
        if data.is_active is not None:
            policy.is_active = data.is_active

        return await self.repository.update_retention_policy(policy)

    async def delete_retention_policy(self, policy_id: UUID) -> bool:
        policy = await self.get_retention_policy(policy_id)
        return await self.repository.delete_retention_policy(policy)

    # Retention Executions
    async def get_retention_execution(self, execution_id: UUID) -> RetentionExecution:
        execution = await self.repository.get_retention_execution(execution_id)
        if not execution:
            raise NotFoundException("Retention execution not found")
        return execution

    async def list_retention_executions(
        self,
        policy_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RetentionExecution], int]:
        return await self.repository.list_retention_executions(
            policy_id=policy_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    # Data Residency Records
    async def create_data_residency_record(self, data: DataResidencyRecordCreate) -> DataResidencyRecord:
        existing = await self.repository.get_data_residency_record_by_entity(data.entity_type, data.entity_id)
        if existing:
            raise ValidationException(f"Data residency record already exists for {data.entity_type}:{data.entity_id}")

        record = DataResidencyRecord(
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            region=data.region,
            legal_basis=data.legal_basis,
            data_categories=data.data_categories,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_data_residency_record(record)

    async def get_data_residency_record(self, record_id: UUID) -> DataResidencyRecord:
        record = await self.repository.get_data_residency_record(record_id)
        if not record:
            raise NotFoundException("Data residency record not found")
        return record

    async def get_data_residency_record_by_entity(self, entity_type: str, entity_id: UUID) -> Optional[DataResidencyRecord]:
        return await self.repository.get_data_residency_record_by_entity(entity_type, entity_id)

    async def list_data_residency_records(
        self,
        entity_type: Optional[str] = None,
        region: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataResidencyRecord], int]:
        return await self.repository.list_data_residency_records(
            entity_type=entity_type,
            region=region,
            page=page,
            page_size=page_size,
        )

    async def update_data_residency_record(self, record_id: UUID, data: DataResidencyRecordUpdate) -> DataResidencyRecord:
        record = await self.get_data_residency_record(record_id)

        if data.region is not None:
            record.region = data.region
        if data.legal_basis is not None:
            record.legal_basis = data.legal_basis
        if data.data_categories is not None:
            record.data_categories = data.data_categories
        if data.verified_at is not None:
            record.verified_at = data.verified_at
            record.verified_by_id = self.user_id

        return await self.repository.update_data_residency_record(record)