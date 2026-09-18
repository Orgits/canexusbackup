from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.ai_processing.schemas import (
    AIConfidenceThresholdCreate,
    AIConfidenceThresholdListResponse,
    AIConfidenceThresholdResponse,
    AIConfidenceThresholdUpdate,
    AIModelCreate,
    AIModelListResponse,
    AIModelResponse,
    AIModelUpdate,
    AIProcessingJobCreate,
    AIProcessingJobListResponse,
    AIProcessingJobResponse,
    AIProcessingJobUpdate,
    AIProcessRequest,
    AIReviewTaskCreate,
    AIReviewTaskListResponse,
    AIReviewTaskResponse,
    AIReviewTaskUpdate,
    AIProcessRequest,
)
from app.modules.ai_processing.service import AIModelService, AIProcessingService, AIConfidenceService, AIReviewTaskService
from app.modules.users.models import User

router = APIRouter(prefix="/ai", tags=["AI Processing"])


# AI Model endpoints
@router.post("/models", response_model=AIModelResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_model(
    data: AIModelCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIModelService(db)
    model = await service.create(data, tenant_context.tenant_id, current_user.id)
    return AIModelResponse.model_validate(model)


@router.get("/models", response_model=AIModelListResponse)
async def list_ai_models(
    page: int = 1,
    page_size: int = 20,
    model_type: str = None,
    provider: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIModelService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, model_type, provider, is_active
    )
    return AIModelListResponse(
        items=[AIModelResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/models/{model_id}", response_model=AIModelResponse)
async def get_ai_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIModelService(db)
    model = await service.get_by_id(model_id, tenant_context.tenant_id)
    return AIModelResponse.model_validate(model)


@router.patch("/models/{model_id}", response_model=AIModelResponse)
async def update_ai_model(
    model_id: UUID,
    data: AIModelUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIModelService(db)
    model = await service.update(model_id, tenant_context.tenant_id, data.model_dump(exclude_unset=True), current_user.id)
    return AIModelResponse.model_validate(model)


@router.post("/models/{model_id}/set-default", response_model=AIModelResponse)
async def set_default_ai_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIModelService(db)
    model = await service.set_default(model_id, tenant_context.tenant_id)
    return AIModelResponse.model_validate(model)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_DELETE)),
):
    service = AIModelService(db)
    await service.delete(model_id, tenant_context.tenant_id)


# AI Processing Job endpoints
@router.post("/jobs", response_model=AIProcessingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_job(
    data: AIProcessingJobCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIProcessingService(db)
    job = await service.create_job(data, tenant_context.tenant_id, current_user.id)
    return AIProcessingJobResponse.model_validate(job)


@router.get("/jobs", response_model=AIProcessingJobListResponse)
async def list_ai_jobs(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    model_id: UUID = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIProcessingService(db)
    items, total = await service.list_jobs(
        tenant_context.tenant_id, page, page_size, status, model_id, date_from, date_to
    )
    return AIProcessingJobListResponse(
        items=[AIProcessingJobResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/jobs/{job_id}", response_model=AIProcessingJobResponse)
async def get_ai_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIProcessingService(db)
    job = await service.get_job(job_id, tenant_context.tenant_id)
    return AIProcessingJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/process", response_model=AIProcessingJobResponse)
async def process_ai_job(
    job_id: UUID,
    request: AIProcessRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIProcessingService(db)
    job = await service.process_document(request, tenant_context.tenant_id, current_user.id)
    return AIProcessingJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/retry", response_model=AIProcessingJobResponse)
async def retry_ai_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIProcessingService(db)
    job = await service.retry_job(job_id, tenant_context.tenant_id)
    return AIProcessingJobResponse.model_validate(job)


@router.get("/jobs", response_model=AIProcessingJobListResponse)
async def list_ai_jobs(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    model_id: UUID = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIProcessingService(db)
    items, total = await service.list_jobs(
        tenant_context.tenant_id, page, page_size, status, model_id, date_from, date_to
    )
    return AIProcessingJobListResponse(
        items=[AIProcessingJobResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/process", response_model=AIProcessingJobResponse)
async def process_document_ai(
    request: AIProcessRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIProcessingService(db)
    job = await service.process_document(request, tenant_context.tenant_id, current_user.id)
    return AIProcessingJobResponse.model_validate(job)


# Confidence Threshold endpoints
@router.post("/thresholds", response_model=AIConfidenceThresholdResponse, status_code=status.HTTP_201_CREATED)
async def create_confidence_threshold(
    data: AIConfidenceThresholdCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIConfidenceService(db)
    threshold = await service.create_threshold(data, tenant_context.tenant_id, current_user.id)
    return AIConfidenceThresholdResponse.model_validate(threshold)


@router.get("/thresholds", response_model=AIConfidenceThresholdListResponse)
async def list_confidence_thresholds(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIConfidenceService(db)
    items = await service.get_all(tenant_context.tenant_id)
    return AIConfidenceThresholdListResponse(
        items=[AIConfidenceThresholdResponse.model_validate(item) for item in items],
        total=len(items),
        page=1,
        page_size=len(items),
        total_pages=1,
    )


@router.get("/thresholds/{model_type}", response_model=AIConfidenceThresholdResponse)
async def get_confidence_threshold(
    model_type: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIConfidenceService(db)
    threshold = await service.get_by_type(model_type, tenant_context.tenant_id)
    if not threshold:
        raise NotFoundException(detail="Confidence threshold not found")
    return AIConfidenceThresholdResponse.model_validate(threshold)


@router.patch("/thresholds/{model_type}", response_model=AIConfidenceThresholdResponse)
async def update_confidence_threshold(
    model_type: str,
    data: AIConfidenceThresholdUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIConfidenceService(db)
    threshold = await service.update(model_type, tenant_context.tenant_id, data.model_dump(exclude_unset=True), current_user.id)
    return AIConfidenceThresholdResponse.model_validate(threshold)


@router.post("/evaluate-confidence", response_model=dict)
async def evaluate_confidence(
    model_type: str,
    confidence: float,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIConfidenceService(db)
    result = await service.evaluate_confidence(model_type, tenant_context.tenant_id, confidence)
    return result


# Review Task endpoints
@router.post("/review-tasks", response_model=AIReviewTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_review_task(
    data: AIReviewTaskCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIReviewTaskService(db)
    task = await service.create_task(data.job_id, tenant_context.tenant_id, data.assignee_id, current_user.id)
    return AIReviewTaskResponse.model_validate(task)


@router.get("/review-tasks", response_model=AIReviewTaskListResponse)
async def list_review_tasks(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    assignee_id: UUID = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIReviewTaskService(db)
    items, total = await service.list_tasks(tenant_context.tenant_id, page, page_size, status, assignee_id)
    return AIReviewTaskListResponse(
        items=[AIReviewTaskResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/review-tasks/{task_id}", response_model=AIReviewTaskResponse)
async def get_review_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = AIReviewTaskService(db)
    task = await service.get_task(task_id, tenant_context.tenant_id)
    return AIReviewTaskResponse.model_validate(task)


@router.patch("/review-tasks/{task_id}", response_model=AIReviewTaskResponse)
async def update_review_task(
    task_id: UUID,
    data: AIReviewTaskUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = AIReviewTaskService(db)
    task = await service.update_task(task_id, tenant_context.tenant_id, data.model_dump(exclude_unset=True), current_user.id)
    return AIReviewTaskResponse.model_validate(task)