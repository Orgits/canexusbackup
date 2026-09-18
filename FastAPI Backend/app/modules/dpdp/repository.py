from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database.base import TenantBaseModelMixin
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


class DPDPRepository:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self, model):
        return select(model).where(model.tenant_id == self.tenant_id)

    # Data Access Requests
    async def get_data_access_request(self, request_id: UUID) -> Optional[DataAccessRequest]:
        query = self._base_query(DataAccessRequest).where(DataAccessRequest.id == request_id).options(
            selectinload(DataAccessRequest.subject),
            selectinload(DataAccessRequest.client),
            selectinload(DataAccessRequest.approved_by),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

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
        query = self._base_query(DataAccessRequest).options(
            selectinload(DataAccessRequest.subject),
            selectinload(DataAccessRequest.client),
            selectinload(DataAccessRequest.approved_by),
        )

        if subject_id:
            query = query.where(DataAccessRequest.subject_id == subject_id)
        if client_id:
            query = query.where(DataAccessRequest.client_id == client_id)
        if status:
            query = query.where(DataAccessRequest.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        sort_column = getattr(DataAccessRequest, sort_by, DataAccessRequest.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_data_access_request(self, request: DataAccessRequest) -> DataAccessRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def update_data_access_request(self, request: DataAccessRequest) -> DataAccessRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    # Data Correction Requests
    async def get_data_correction_request(self, request_id: UUID) -> Optional[DataCorrectionRequest]:
        query = self._base_query(DataCorrectionRequest).where(DataCorrectionRequest.id == request_id).options(
            selectinload(DataCorrectionRequest.subject),
            selectinload(DataCorrectionRequest.client),
            selectinload(DataCorrectionRequest.reviewed_by),
            selectinload(DataCorrectionRequest.applied_by),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

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
        query = self._base_query(DataCorrectionRequest).options(
            selectinload(DataCorrectionRequest.subject),
            selectinload(DataCorrectionRequest.client),
            selectinload(DataCorrectionRequest.reviewed_by),
            selectinload(DataCorrectionRequest.applied_by),
        )

        if subject_id:
            query = query.where(DataCorrectionRequest.subject_id == subject_id)
        if client_id:
            query = query.where(DataCorrectionRequest.client_id == client_id)
        if entity_type:
            query = query.where(DataCorrectionRequest.entity_type == entity_type)
        if status:
            query = query.where(DataCorrectionRequest.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        sort_column = getattr(DataCorrectionRequest, sort_by, DataCorrectionRequest.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_data_correction_request(self, request: DataCorrectionRequest) -> DataCorrectionRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def update_data_correction_request(self, request: DataCorrectionRequest) -> DataCorrectionRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    # Data Erasure Requests
    async def get_data_erasure_request(self, request_id: UUID) -> Optional[DataErasureRequest]:
        query = self._base_query(DataErasureRequest).where(DataErasureRequest.id == request_id).options(
            selectinload(DataErasureRequest.subject),
            selectinload(DataErasureRequest.client),
            selectinload(DataErasureRequest.approved_by),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

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
        query = self._base_query(DataErasureRequest).options(
            selectinload(DataErasureRequest.subject),
            selectinload(DataErasureRequest.client),
            selectinload(DataErasureRequest.approved_by),
        )

        if subject_id:
            query = query.where(DataErasureRequest.subject_id == subject_id)
        if client_id:
            query = query.where(DataErasureRequest.client_id == client_id)
        if status:
            query = query.where(DataErasureRequest.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        sort_column = getattr(DataErasureRequest, sort_by, DataErasureRequest.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_data_erasure_request(self, request: DataErasureRequest) -> DataErasureRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def update_data_erasure_request(self, request: DataErasureRequest) -> DataErasureRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    # Retention Policies
    async def get_retention_policy(self, policy_id: UUID) -> Optional[RetentionPolicy]:
        query = self._base_query(RetentionPolicy).where(RetentionPolicy.id == policy_id).options(
            selectinload(RetentionPolicy.created_by),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_retention_policies(
        self,
        entity_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[RetentionPolicy], int]:
        query = self._base_query(RetentionPolicy).options(selectinload(RetentionPolicy.created_by))

        if entity_type:
            query = query.where(RetentionPolicy.entity_type == entity_type)
        if is_active is not None:
            query = query.where(RetentionPolicy.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        sort_column = getattr(RetentionPolicy, sort_by, RetentionPolicy.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_retention_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        self.db.add(policy)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def update_retention_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def delete_retention_policy(self, policy: RetentionPolicy) -> bool:
        await self.db.delete(policy)
        await self.db.flush()
        return True

    # Retention Executions
    async def get_retention_execution(self, execution_id: UUID) -> Optional[RetentionExecution]:
        query = self._base_query(RetentionExecution).where(RetentionExecution.id == execution_id).options(
            selectinload(RetentionExecution.policy),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_retention_executions(
        self,
        policy_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RetentionExecution], int]:
        query = self._base_query(RetentionExecution).options(selectinload(RetentionExecution.policy))

        if policy_id:
            query = query.where(RetentionExecution.policy_id == policy_id)
        if status:
            query = query.where(RetentionExecution.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = query.order_by(desc(RetentionExecution.executed_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_retention_execution(self, execution: RetentionExecution) -> RetentionExecution:
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def update_retention_execution(self, execution: RetentionExecution) -> RetentionExecution:
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    # Data Residency Records
    async def get_data_residency_record(self, record_id: UUID) -> Optional[DataResidencyRecord]:
        query = self._base_query(DataResidencyRecord).where(DataResidencyRecord.id == record_id).options(
            selectinload(DataResidencyRecord.verified_by),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_data_residency_record_by_entity(self, entity_type: str, entity_id: UUID) -> Optional[DataResidencyRecord]:
        query = self._base_query(DataResidencyRecord).where(
            and_(
                DataResidencyRecord.entity_type == entity_type,
                DataResidencyRecord.entity_id == entity_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_data_residency_records(
        self,
        entity_type: Optional[str] = None,
        region: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataResidencyRecord], int]:
        query = self._base_query(DataResidencyRecord).options(selectinload(DataResidencyRecord.verified_by))

        if entity_type:
            query = query.where(DataResidencyRecord.entity_type == entity_type)
        if region:
            query = query.where(DataResidencyRecord.region == region)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = query.order_by(desc(DataResidencyRecord.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_data_residency_record(self, record: DataResidencyRecord) -> DataResidencyRecord:
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update_data_residency_record(self, record: DataResidencyRecord) -> DataResidencyRecord:
        await self.db.flush()
        await self.db.refresh(record)
        return record