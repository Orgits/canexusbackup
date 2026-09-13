from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from app.core.database import get_async_db
from app.core.tenancy.dependencies import get_current_tenant
from app.core.security.dependencies import get_current_active_user
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.modules.documents.schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadInitRequest,
    DocumentUploadInitResponse,
)
from app.modules.documents.service import DocumentService
from app.modules.users.models import User

router = APIRouter()


@router.post("/upload/init", response_model=DocumentUploadInitResponse, status_code=status.HTTP_201_CREATED)
async def init_document_upload(
    data: DocumentUploadInitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = DocumentService(db)
    return await service.init_upload(data, current_tenant.id, current_user.id)


@router.post("/upload/complete/{document_id}", response_model=DocumentResponse)
async def complete_document_upload(
    document_id: UUID,
    checksum: str,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = DocumentService(db)
    document = await service.complete_upload(document_id, current_tenant.id, checksum)
    return DocumentResponse.model_validate(document)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = DocumentService(db)
    document = await service.init_upload(
        DocumentUploadInitRequest(
            filename=data.filename,
            file_size=data.file_size,
            mime_type=data.mime_type,
            client_id=data.client_id,
            matter_id=data.matter_id,
            category=data.category,
            title=data.title,
            description=data.description,
            tags=data.tags,
        ),
        current_tenant.id,
        current_user.id,
    )
    document = await service.complete_upload(document.document_id, current_tenant.id, "")
    return DocumentResponse.model_validate(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    matter_id: UUID = None,
    task_id: UUID = None,
    compliance_cycle_id: UUID = None,
    status: str = None,
    category: str = None,
    uploaded_by: UUID = None,
    date_from: datetime = None,
    date_to: datetime = None,
    tags: str = None,
    sort_by: str = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = DocumentService(db)
    tag_list = tags.split(",") if tags else None
    items, total = await service.get_all(
        current_tenant.id, page, page_size, search, client_id, matter_id, task_id,
        compliance_cycle_id, status, category, uploaded_by, date_from, date_to,
        tag_list, sort_by, sort_order
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    service = DocumentService(db)
    document = await service.get_by_id(document_id, current_tenant.id)
    return DocumentResponse.model_validate(document)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = DocumentService(db)
    document = await service.update(document_id, current_tenant.id, data, current_user.id)
    return DocumentResponse.model_validate(document)


@router.post("/{document_id}/version", response_model=DocumentUploadInitResponse, status_code=status.HTTP_201_CREATED)
async def create_document_version(
    document_id: UUID,
    data: DocumentUploadInitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    service = DocumentService(db)
    return await service.create_new_version(document_id, current_tenant.id, data, current_user.id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_DELETE)),
):
    service = DocumentService(db)
    await service.delete(document_id, current_tenant.id)
    return None