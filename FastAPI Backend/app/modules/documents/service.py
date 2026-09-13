from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException
from app.modules.documents.models import Document, DocumentStatus, DocumentCategory
from app.modules.documents.schemas import DocumentCreate, DocumentUpdate, DocumentUploadInitRequest, DocumentUploadInitResponse
from app.modules.documents.repository import DocumentRepository
from app.modules.clients.models import Client
from app.modules.matters.models import Matter
from app.modules.tasks.models import Task
from app.modules.compliance.models import ComplianceCycle
from app.modules.users.models import User


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentRepository(db)

    async def init_upload(self, data: DocumentUploadInitRequest, tenant_id: UUID, uploaded_by: UUID) -> DocumentUploadInitResponse:
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        if data.matter_id:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == data.matter_id, Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        document_id = UUID(bytes=b'\x00' * 16)  # Will be generated
        storage_key = f"{tenant_id}/{data.client_id}/{document_id}/{data.filename}"

        document = Document(
            client_id=data.client_id,
            matter_id=data.matter_id,
            filename=data.filename,
            original_filename=data.filename,
            file_extension=data.filename.split(".")[-1] if "." in data.filename else "",
            mime_type=data.mime_type,
            file_size=data.file_size,
            storage_path=storage_key,
            storage_key=storage_key,
            category=data.category,
            title=data.title,
            description=data.description,
            tags=data.tags,
            source="manual",
            uploaded_by=uploaded_by,
            tenant_id=tenant_id,
            created_by=uploaded_by,
            status=DocumentStatus.UPLOADED,
        )
        document = await self.repository.create(document)

        upload_url = f"https://storage.example.com/upload/{document.id}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        return DocumentUploadInitResponse(
            upload_url=upload_url,
            document_id=document.id,
            storage_key=storage_key,
            expires_at=expires_at,
        )

    async def complete_upload(self, document_id: UUID, tenant_id: UUID, checksum: str) -> Document:
        document = await self.get_by_id(document_id, tenant_id)
        document.checksum = checksum
        document.status = DocumentStatus.PROCESSED
        return await self.repository.update(document)

    async def get_by_id(self, document_id: UUID, tenant_id: UUID) -> Document:
        document = await self.repository.get_by_id(document_id, tenant_id)
        if not document:
            raise NotFoundException(detail="Document not found")
        return document

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        matter_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        compliance_cycle_id: Optional[UUID] = None,
        status: Optional[DocumentStatus] = None,
        category: Optional[DocumentCategory] = None,
        uploaded_by: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Document], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, matter_id, task_id,
            compliance_cycle_id, status, category, uploaded_by, date_from, date_to,
            tags, sort_by, sort_order
        )

    async def update(self, document_id: UUID, tenant_id: UUID, data: DocumentUpdate, updated_by: UUID) -> Document:
        document = await self.get_by_id(document_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if "matter_id" in update_data and update_data["matter_id"]:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == update_data["matter_id"], Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        if "task_id" in update_data and update_data["task_id"]:
            task_result = await self.db.execute(
                select(Task).where(Task.id == update_data["task_id"], Task.tenant_id == tenant_id)
            )
            if not task_result.scalar_one_or_none():
                raise NotFoundException(detail="Task not found")

        if "compliance_cycle_id" in update_data and update_data["compliance_cycle_id"]:
            cycle_result = await self.db.execute(
                select(ComplianceCycle).where(ComplianceCycle.id == update_data["compliance_cycle_id"], ComplianceCycle.tenant_id == tenant_id)
            )
            if not cycle_result.scalar_one_or_none():
                raise NotFoundException(detail="Compliance cycle not found")

        for field, value in update_data.items():
            setattr(document, field, value)
        document.updated_by = updated_by
        return await self.repository.update(document)

    async def create_new_version(
        self,
        document_id: UUID,
        tenant_id: UUID,
        data: DocumentUploadInitRequest,
        uploaded_by: UUID,
    ) -> DocumentUploadInitResponse:
        old_document = await self.get_by_id(document_id, tenant_id)

        if old_document.client_id != data.client_id:
            raise ConflictException(detail="Cannot change client for new version")

        old_document.is_latest_version = False
        await self.repository.update(old_document)

        storage_key = f"{tenant_id}/{data.client_id}/{old_document.id}/v{old_document.version + 1}/{data.filename}"

        new_document = Document(
            client_id=data.client_id,
            matter_id=data.matter_id,
            filename=data.filename,
            original_filename=data.filename,
            file_extension=data.filename.split(".")[-1] if "." in data.filename else "",
            mime_type=data.mime_type,
            file_size=data.file_size,
            storage_path=storage_key,
            storage_key=storage_key,
            category=data.category,
            title=data.title,
            description=data.description,
            tags=data.tags,
            source="manual",
            uploaded_by=uploaded_by,
            tenant_id=tenant_id,
            created_by=uploaded_by,
            status=DocumentStatus.UPLOADED,
            version=old_document.version + 1,
            previous_version_id=old_document.id,
        )
        new_document = await self.repository.create_version(new_document)

        upload_url = f"https://storage.example.com/upload/{new_document.id}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        return DocumentUploadInitResponse(
            upload_url=upload_url,
            document_id=new_document.id,
            storage_key=storage_key,
            expires_at=expires_at,
        )

    async def delete(self, document_id: UUID, tenant_id: UUID) -> None:
        document = await self.get_by_id(document_id, tenant_id)
        await self.repository.delete(document)