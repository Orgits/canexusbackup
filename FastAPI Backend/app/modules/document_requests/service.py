from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.clients.models import Client
from app.modules.document_requests.models import DocumentRequest, DocumentRequestDocument, DocumentRequestStatus, DocumentRequestPriority
from app.modules.document_requests.repository import DocumentRequestRepository
from app.modules.document_requests.schemas import DocumentRequestCreate, DocumentRequestUpdate, DocumentRequestDocumentCreate
from app.modules.users.models import User


class DocumentRequestService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentRequestRepository(db)

    async def create(self, data: DocumentRequestCreate, tenant_id: UUID, created_by: UUID) -> DocumentRequest:
        # Validate client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        # Validate assignee if provided
        if data.assigned_to:
            assignee_result = await self.db.execute(
                select(User).where(User.id == data.assigned_to, User.tenant_id == tenant_id)
            )
            if not assignee_result.scalar_one_or_none():
                raise NotFoundException(detail="Assignee not found")

        request = DocumentRequest(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=DocumentRequestStatus.DRAFT,
        )
        return await self.repository.create(request)

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> DocumentRequest:
        request = await self.repository.get_by_id(request_id, tenant_id)
        if not request:
            raise NotFoundException(detail="Document request not found")
        return request

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        assigned_to: UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, matter_id, assigned_to,
            status, priority, date_from, date_to, sort_by, sort_order
        )

    async def update(self, request_id: UUID, tenant_id: UUID, data: DocumentRequestUpdate, updated_by: UUID) -> DocumentRequest:
        request = await self.get_by_id(request_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(request, field, value)

        request.updated_at = datetime.now()
        request.updated_by = updated_by
        return await self.repository.update(request)

    async def send(self, request_id: UUID, tenant_id: UUID, sent_by: UUID) -> dict:
        request = await self.get_by_id(request_id, tenant_id)
        if request.status != DocumentRequestStatus.DRAFT:
            raise ValueError("Can only send draft requests")

        request.status = DocumentRequestStatus.SENT
        request.submitted_at = datetime.now()
        request.updated_at = datetime.now()
        request.updated_by = sent_by

        # Create document records
        for req_doc in request.required_documents:
            doc = DocumentRequestDocument(
                request_id=request.id,
                document_id=req_doc.get("document_id"),
                document_name=req_doc.get("name"),
                document_type=req_doc.get("type"),
                is_required=req_doc.get("required", True),
                tenant_id=request.tenant_id,
            )
            self.db.add(doc)

        await self.db.flush()
        await self.db.refresh(request)

        return {"message": "Document request sent", "request_id": str(request.id)}

    async def submit_document(
        self, request_id: UUID, tenant_id: UUID, document_id: UUID, uploaded_by: UUID
    ) -> dict:
        request = await self.get_by_id(request_id, tenant_id)

        # Update document record
        result = await self.db.execute(
            select(DocumentRequestDocument).where(
                DocumentRequestDocument.request_id == request_id,
                DocumentRequestDocument.document_id == document_id,
                DocumentRequestDocument.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc:
            doc.uploaded_by = uploaded_by
            doc.uploaded_at = datetime.now()

        # Update submitted documents in request
        submitted = list(request.submitted_documents)
        submitted.append({"document_id": str(document_id), "uploaded_at": datetime.now().isoformat()})
        request.submitted_documents = submitted

        # Check if all required documents submitted
        required_count = sum(1 for d in request.required_documents if d.get("required", True))
        submitted_count = len(request.submitted_documents)

        if submitted_count >= required_count and request.status == DocumentRequestStatus.IN_PROGRESS:
            request.status = DocumentRequestStatus.SUBMITTED
            request.submitted_at = datetime.now()

        await self.db.flush()
        await self.db.refresh(request)

        return {"message": "Document submitted", "request_id": str(request.id)}

    async def review(self, request_id: UUID, tenant_id: UUID, action: str, reviewed_by: UUID, notes: str = None) -> dict:
        request = await self.get_by_id(request_id, tenant_id)

        if action == "approve":
            request.status = DocumentRequestStatus.APPROVED
        elif action == "reject":
            request.status = DocumentRequestStatus.REJECTED
        else:
            raise ValueError("Invalid action. Must be 'approve' or 'reject'")

        request.reviewed_at = datetime.now()
        request.reviewed_by = reviewed_by
        request.notes = notes

        await self.db.flush()
        await self.db.refresh(request)

        return {"message": f"Document request {action}d", "request_id": str(request.id)}

    async def send_reminder(self, request_id: UUID, tenant_id: UUID, sent_by: UUID) -> dict:
        request = await self.get_by_id(request_id, tenant_id)
        if request.status not in [DocumentRequestStatus.SENT, DocumentRequestStatus.IN_PROGRESS]:
            raise ValueError("Can only send reminders for sent or in-progress requests")

        request.reminder_sent_at = datetime.now()
        request.reminder_count += 1
        request.updated_at = datetime.now()
        request.updated_by = sent_by

        await self.db.flush()
        await self.db.refresh(request)

        return {"message": "Reminder sent", "request_id": str(request.id)}

    async def cancel(self, request_id: UUID, tenant_id: UUID) -> dict:
        request = await self.get_by_id(request_id, tenant_id)
        if request.status in [DocumentRequestStatus.APPROVED, DocumentRequestStatus.REJECTED]:
            raise ValueError("Cannot cancel completed request")

        request.status = DocumentRequestStatus.CANCELLED
        request.updated_at = datetime.now()

        await self.db.flush()
        return {"message": "Document request cancelled", "request_id": str(request.id)}