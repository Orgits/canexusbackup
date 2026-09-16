from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.ocr.schemas import (
    OCRJobCreate,
    OCRJobListResponse,
    OCRJobResponse,
    OCRJobUpdate,
    OCRProcessRequest,
    OCRTemplateCreate,
    OCRTemplateListResponse,
    OCRTemplateResponse,
    OCRTemplateUpdate,
)
from app.modules.ocr.service import OCRService
from app.modules.users.models import User

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/jobs", response_model=OCRJobResponse, status_code=status.HTTP_201_CREATED)
async def create_ocr_job(
    data: OCRJobCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = OCRService(db)
    job = await service.create_job(data, tenant_context.tenant_id, current_user.id)
    return OCRJobResponse.model_validate(job)


@router.get("/jobs", response_model=OCRJobListResponse)
async def list_ocr_jobs(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    engine: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = OCRService(db)
    items, total = await service.list_jobs(tenant_context.tenant_id, page, page_size, status, engine, date_from, date_to)
    return OCRJobListResponse(
        items=[OCRJobResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/jobs/{job_id}", response_model=OCRJobResponse)
async def get_ocr_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = OCRService(db)
    job = await service.get_job(job_id, tenant_context.tenant_id)
    return OCRJobResponse.model_validate(job)


@router.patch("/jobs/{job_id}", response_model=OCRJobResponse)
async def update_ocr_job(
    job_id: UUID,
    data: OCRJobUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPDATE)),
):
    service = OCRService(db)
    job = await service.get_job(job_id, tenant_context.tenant_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.flush()
    await db.refresh(job)

    return OCRJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/process", response_model=OCRJobResponse)
async def process_ocr_job(
    job_id: UUID,
    request: OCRProcessRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = OCRService(db)
    job = await service.process_document(request, tenant_context.tenant_id, current_user.id)
    return OCRJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/retry", response_model=OCRJobResponse)
async def retry_ocr_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = OCRService(db)
    job = await service.retry_job(job_id, tenant_context.tenant_id)
    return OCRJobResponse.model_validate(job)


@router.get("/jobs", response_model=OCRJobListResponse)
async def list_ocr_jobs(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    engine: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = OCRService(db)
    items, total = await service.list_jobs(tenant_context.tenant_id, page, page_size, status, engine, date_from, date_to)
    return OCRJobListResponse(
        items=[OCRJobResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# Template endpoints
@router.post("/templates", response_model=OCRTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_ocr_template(
    data: OCRTemplateCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = OCRService(db)
    template = await service.create_template(data, tenant_context.tenant_id, current_user.id)
    return OCRTemplateResponse.model_validate(template)


@router.get("/templates", response_model=OCRTemplateListResponse)
async def list_ocr_templates(
    page: int = 1,
    page_size: int = 20,
    engine: str = None,
    is_active: bool = None,
    is_default: bool = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = OCRService(db)
    items, total = await service.list_templates(tenant_context.tenant_id, page, page_size, engine, is_active, is_default)
    return OCRTemplateListResponse(
        items=[OCRTemplateResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/templates/{template_id}", response_model=OCRTemplateResponse)
async def get_ocr_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = OCRService(db)
    template = await service.get_template(template_id, tenant_context.tenant_id)
    return OCRTemplateResponse.model_validate(template)


@router.patch("/templates/{template_id}", response_model=OCRTemplateResponse)
async def update_ocr_template(
    template_id: UUID,
    data: OCRTemplateUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPDATE)),
):
    service = OCRService(db)
    template = await service.update_template(template_id, tenant_context.tenant_id, data, current_user.id)
    return OCRTemplateResponse.model_validate(template)


@router.post("/templates/{template_id}/set-default", response_model=OCRTemplateResponse)
async def set_default_ocr_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPDATE)),
):
    service = OCRService(db)
    template = await service.set_default_template(template_id, tenant_context.tenant_id)
    return OCRTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ocr_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_DELETE)),
):
    service = OCRService(db)
    await service.delete_template(template_id, tenant_context.tenant_id)