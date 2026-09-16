from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.document_requests.schemas import (
    DocumentRequestCreate,
    DocumentRequestDetailResponse,
    DocumentRequestListResponse,
    DocumentRequestResponse,
    DocumentRequestUpdate,
)
from app.modules.document_requests.service import DocumentRequestService
from app.modules.users.models import User

router = APIRouter(prefix="/document-requests", tags=["Document Requests"])


@router.post("", response_model=DocumentRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_document_request(
    data: DocumentRequestCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_CREATE)),
):
    service = DocumentRequestService(db)
    request = await service.create(data, tenant_context.tenant_id, current_user.id)
    return DocumentRequestResponse.model_validate(request)


@router.get("", response_model=DocumentRequestListResponse)
async def list_document_requests(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    matter_id: UUID = None,
    assigned_to: UUID = None,
    status: str = None,
    priority: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    sort_by: str = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_READ)),
):
    service = DocumentRequestService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, client_id, matter_id,
        assigned_to, status, priority, date_from, date_to, sort_by, sort_order
    )
    return DocumentRequestListResponse(
        items=[DocumentRequestResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{request_id}", response_model=DocumentRequestResponse)
async def get_document_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_READ)),
):
    service = DocumentRequestService(db)
    request = await service.get_by_id(request_id, tenant_context.tenant_id)
    return DocumentRequestResponse.model_validate(request)


@router.patch("/{request_id}", response_model=DocumentRequestResponse)
async def update_document_request(
    request_id: UUID,
    data: DocumentRequestUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_UPDATE)),
):
    service = DocumentRequestService(db)
    request = await service.update(request_id, tenant_context.tenant_id, data, current_user.id)
    return DocumentRequestResponse.model_validate(request)


@router.post("/{request_id}/send", response_model=dict)
async def send_document_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_SEND)),
):
    service = DocumentRequestService(db)
    result = await service.send(request_id, tenant_context.tenant_id, current_user.id)
    return result


@router.post("/{request_id}/documents", status_code=status.HTTP_201_CREATED)
async def submit_document(
    request_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_UPDATE)),
):
    service = DocumentRequestService(db)
    result = await service.submit_document(request_id, tenant_context.tenant_id, document_id, current_user.id)
    return result


@router.post("/{request_id}/review", response_model=dict)
async def review_document_request(
    request_id: UUID,
    action: str,
    notes: str = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_UPDATE)),
):
    service = DocumentRequestService(db)
    result = await service.review(request_id, tenant_context.tenant_id, action, current_user.id, notes)
    return result


@router.post("/{request_id}/remind", response_model=dict)
async def send_reminder(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_UPDATE)),
):
    service = DocumentRequestService(db)
    result = await service.send_reminder(request_id, tenant_context.tenant_id, current_user.id)
    return result


@router.post("/{request_id}/cancel", response_model=dict)
async def cancel_document_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_DELETE)),
):
    service = DocumentRequestService(db)
    result = await service.cancel(request_id, tenant_context.tenant_id)
    return result


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_DELETE)),
):
    service = DocumentRequestService(db)
    await service.delete(request_id, tenant_context.tenant_id)