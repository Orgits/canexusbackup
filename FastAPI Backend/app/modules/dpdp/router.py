from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.tenancy import get_tenant_context, TenantContext
from app.modules.dpdp.schemas import (
    DataAccessRequestCreate,
    DataAccessRequestUpdate,
    DataAccessRequestResponse,
    DataAccessRequestListResponse,
    DataCorrectionRequestCreate,
    DataCorrectionRequestUpdate,
    DataCorrectionRequestResponse,
    DataCorrectionRequestListResponse,
    DataErasureRequestCreate,
    DataErasureRequestUpdate,
    DataErasureRequestResponse,
    DataErasureRequestListResponse,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
    RetentionPolicyResponse,
    RetentionPolicyListResponse,
    RetentionExecutionResponse,
    DataResidencyRecordCreate,
    DataResidencyRecordUpdate,
    DataResidencyRecordResponse,
    DataResidencyRecordListResponse,
)
from app.modules.dpdp.service import DPDPService
from app.modules.dpdp.models import (
    DataAccessStatus,
    DataCorrectionStatus,
    DataErasureStatus,
    RetentionAction,
)

router = APIRouter()


async def get_dpdp_service(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> DPDPService:
    from app.modules.users.models import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == tenant_context.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    return DPDPService(db, tenant_context.tenant_id, user.id)


@router.post("/access-requests", response_model=DataAccessRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("dpdp_access.create"))])
async def create_data_access_request(
    data: DataAccessRequestCreate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.create_data_access_request(data)


@router.get("/access-requests", response_model=list[DataAccessRequestListResponse], dependencies=[Depends(require_permission("dpdp_access.read"))])
async def list_data_access_requests(
    subject_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    status: Optional[DataAccessStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    service: DPDPService = Depends(get_dpdp_service),
):
    requests, _ = await service.list_data_access_requests(
        subject_id=subject_id,
        client_id=client_id,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return requests


@router.get("/access-requests/{request_id}", response_model=DataAccessRequestResponse, dependencies=[Depends(require_permission("dpdp_access.read"))])
async def get_data_access_request(
    request_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.get_data_access_request(request_id)


@router.patch("/access-requests/{request_id}", response_model=DataAccessRequestResponse, dependencies=[Depends(require_permission("dpdp_access.create"))])
async def update_data_access_request(
    request_id: UUID,
    data: DataAccessRequestUpdate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.update_data_access_request(request_id, data)


@router.post("/access-requests/{request_id}/approve", response_model=DataAccessRequestResponse, dependencies=[Depends(require_permission("dpdp_access.create"))])
async def approve_data_access_request(
    request_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.approve_data_access_request(request_id)


@router.post("/access-requests/{request_id}/reject", response_model=DataAccessRequestResponse, dependencies=[Depends(require_permission("dpdp_access.create"))])
async def reject_data_access_request(
    request_id: UUID,
    reason: str = Query(...),
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.reject_data_access_request(request_id, reason)


@router.post("/correction-requests", response_model=DataCorrectionRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("dpdp_correction.create"))])
async def create_data_correction_request(
    data: DataCorrectionRequestCreate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.create_data_correction_request(data)


@router.get("/correction-requests", response_model=list[DataCorrectionRequestListResponse], dependencies=[Depends(require_permission("dpdp_correction.read"))])
async def list_data_correction_requests(
    subject_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    entity_type: Optional[str] = Query(None),
    status: Optional[DataCorrectionStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    service: DPDPService = Depends(get_dpdp_service),
):
    requests, _ = await service.list_data_correction_requests(
        subject_id=subject_id,
        client_id=client_id,
        entity_type=entity_type,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return requests


@router.get("/correction-requests/{request_id}", response_model=DataCorrectionRequestResponse, dependencies=[Depends(require_permission("dpdp_correction.read"))])
async def get_data_correction_request(
    request_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.get_data_correction_request(request_id)


@router.patch("/correction-requests/{request_id}", response_model=DataCorrectionRequestResponse, dependencies=[Depends(require_permission("dpdp_correction.update"))])
async def update_data_correction_request(
    request_id: UUID,
    data: DataCorrectionRequestUpdate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.update_data_correction_request(request_id, data)


@router.post("/correction-requests/{request_id}/approve", response_model=DataCorrectionRequestResponse, dependencies=[Depends(require_permission("dpdp_correction.update"))])
async def approve_data_correction_request(
    request_id: UUID,
    review_notes: Optional[str] = Query(None),
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.approve_data_correction_request(request_id, review_notes)


@router.post("/correction-requests/{request_id}/reject", response_model=DataCorrectionRequestResponse, dependencies=[Depends(require_permission("dpdp_correction.update"))])
async def reject_data_correction_request(
    request_id: UUID,
    review_notes: str = Query(...),
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.reject_data_correction_request(request_id, review_notes)


@router.post("/correction-requests/{request_id}/apply", response_model=DataCorrectionRequestResponse, dependencies=[Depends(require_permission("dpdp_correction.update"))])
async def apply_data_correction(
    request_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.apply_data_correction(request_id)


@router.post("/erasure-requests", response_model=DataErasureRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("dpdp_erasure.create"))])
async def create_data_erasure_request(
    data: DataErasureRequestCreate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.create_data_erasure_request(data)


@router.get("/erasure-requests", response_model=list[DataErasureRequestListResponse], dependencies=[Depends(require_permission("dpdp_erasure.read"))])
async def list_data_erasure_requests(
    subject_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    status: Optional[DataErasureStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    service: DPDPService = Depends(get_dpdp_service),
):
    requests, _ = await service.list_data_erasure_requests(
        subject_id=subject_id,
        client_id=client_id,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return requests


@router.get("/erasure-requests/{request_id}", response_model=DataErasureRequestResponse, dependencies=[Depends(require_permission("dpdp_erasure.read"))])
async def get_data_erasure_request(
    request_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.get_data_erasure_request(request_id)


@router.patch("/erasure-requests/{request_id}", response_model=DataErasureRequestResponse, dependencies=[Depends(require_permission("dpdp_erasure.create"))])
async def update_data_erasure_request(
    request_id: UUID,
    data: DataErasureRequestUpdate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.update_data_erasure_request(request_id, data)


@router.post("/erasure-requests/{request_id}/approve", response_model=DataErasureRequestResponse, dependencies=[Depends(require_permission("dpdp_erasure.execute"))])
async def approve_data_erasure_request(
    request_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.approve_data_erasure_request(request_id)


@router.post("/erasure-requests/{request_id}/reject", response_model=DataErasureRequestResponse, dependencies=[Depends(require_permission("dpdp_erasure.execute"))])
async def reject_data_erasure_request(
    request_id: UUID,
    reason: str = Query(...),
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.reject_data_erasure_request(request_id, reason)


@router.post("/retention-policies", response_model=RetentionPolicyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("retention.create"))])
async def create_retention_policy(
    data: RetentionPolicyCreate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.create_retention_policy(data)


@router.get("/retention-policies", response_model=list[RetentionPolicyListResponse], dependencies=[Depends(require_permission("retention.read"))])
async def list_retention_policies(
    entity_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    service: DPDPService = Depends(get_dpdp_service),
):
    policies, _ = await service.list_retention_policies(
        entity_type=entity_type,
        is_active=is_active,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return policies


@router.get("/retention-policies/{policy_id}", response_model=RetentionPolicyResponse, dependencies=[Depends(require_permission("retention.read"))])
async def get_retention_policy(
    policy_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.get_retention_policy(policy_id)


@router.patch("/retention-policies/{policy_id}", response_model=RetentionPolicyResponse, dependencies=[Depends(require_permission("retention.update"))])
async def update_retention_policy(
    policy_id: UUID,
    data: RetentionPolicyUpdate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.update_retention_policy(policy_id, data)


@router.delete("/retention-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("retention.delete"))])
async def delete_retention_policy(
    policy_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    await service.delete_retention_policy(policy_id)


@router.get("/retention-executions", response_model=list[RetentionExecutionResponse], dependencies=[Depends(require_permission("retention.read"))])
async def list_retention_executions(
    policy_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DPDPService = Depends(get_dpdp_service),
):
    executions, _ = await service.list_retention_executions(
        policy_id=policy_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return executions


@router.get("/retention-executions/{execution_id}", response_model=RetentionExecutionResponse, dependencies=[Depends(require_permission("retention.read"))])
async def get_retention_execution(
    execution_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.get_retention_execution(execution_id)


@router.post("/residency-records", response_model=DataResidencyRecordResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("dpdp_residency.read"))])
async def create_data_residency_record(
    data: DataResidencyRecordCreate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.create_data_residency_record(data)


@router.get("/residency-records", response_model=list[DataResidencyRecordListResponse], dependencies=[Depends(require_permission("dpdp_residency.read"))])
async def list_data_residency_records(
    entity_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DPDPService = Depends(get_dpdp_service),
):
    records, _ = await service.list_data_residency_records(
        entity_type=entity_type,
        region=region,
        page=page,
        page_size=page_size,
    )
    return records


@router.get("/residency-records/{record_id}", response_model=DataResidencyRecordResponse, dependencies=[Depends(require_permission("dpdp_residency.read"))])
async def get_data_residency_record(
    record_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.get_data_residency_record(record_id)


@router.get("/residency-records/by-entity/{entity_type}/{entity_id}", response_model=DataResidencyRecordResponse, dependencies=[Depends(require_permission("dpdp_residency.read"))])
async def get_data_residency_record_by_entity(
    entity_type: str,
    entity_id: UUID,
    service: DPDPService = Depends(get_dpdp_service),
):
    record = await service.get_data_residency_record_by_entity(entity_type, entity_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Data residency record not found")
    return record


@router.patch("/residency-records/{record_id}", response_model=DataResidencyRecordResponse, dependencies=[Depends(require_permission("dpdp_residency.read"))])
async def update_data_residency_record(
    record_id: UUID,
    data: DataResidencyRecordUpdate,
    service: DPDPService = Depends(get_dpdp_service),
):
    return await service.update_data_residency_record(record_id, data)