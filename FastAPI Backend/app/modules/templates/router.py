from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.templates.schemas import (
    TemplateCreate,
    TemplateDetailResponse,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdate,
    TemplateVersionCreate,
)
from app.modules.templates.service import TemplateService
from app.modules.users.models import User

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_CREATE)),
):
    service = TemplateService(db)
    template = await service.create(data, tenant_context.tenant_id, current_user.id)
    return TemplateResponse.model_validate(template)


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = None,
    status: str = None,
    category: str = None,
    channel: str = None,
    is_default: bool = None,
    sort_by: str = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = TemplateService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, status, category, channel, is_default, sort_by, sort_order
    )
    return TemplateListResponse(
        items=[TemplateResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = TemplateService(db)
    template = await service.get_by_id(template_id, tenant_context.tenant_id)
    return TemplateDetailResponse.model_validate(template)


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_UPDATE)),
):
    service = TemplateService(db)
    template = await service.update(template_id, tenant_context.tenant_id, data, current_user.id)
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_DELETE)),
):
    service = TemplateService(db)
    await service.delete(template_id, tenant_context.tenant_id)


@router.post("/{template_id}/version", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template_version(
    template_id: UUID,
    data: TemplateVersionCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_CREATE)),
):
    service = TemplateService(db)
    template = await service.create_version(template_id, tenant_context.tenant_id, data, current_user.id)
    return TemplateResponse.model_validate(template)


@router.post("/{template_id}/activate", response_model=TemplateResponse)
async def activate_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_UPDATE)),
):
    service = TemplateService(db)
    template = await service.activate(template_id, tenant_context.tenant_id)
    return TemplateResponse.model_validate(template)


@router.post("/{template_id}/archive", response_model=TemplateResponse)
async def archive_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_UPDATE)),
):
    service = TemplateService(db)
    template = await service.archive(template_id, tenant_context.tenant_id)
    return TemplateResponse.model_validate(template)


@router.post("/{template_id}/set-default", response_model=TemplateResponse)
async def set_default_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_UPDATE)),
):
    service = TemplateService(db)
    template = await service.set_default(template_id, tenant_context.tenant_id)
    return TemplateResponse.model_validate(template)