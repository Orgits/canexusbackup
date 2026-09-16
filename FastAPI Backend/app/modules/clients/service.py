from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.billing.models import Invoice
from app.modules.clients.models import Client, ClientCategory, ClientContact, ClientService, ClientStatus
from app.modules.clients.repository import ClientContactRepository, ClientRepository, ClientServiceRepository
from app.modules.clients.schemas import (
    ClientCreate,
    ClientUpdate,
    ContactCreate,
    ContactUpdate,
    ServiceCreate,
    ServiceUpdate,
)
from app.modules.compliance.models import ComplianceCycle
from app.modules.documents.models import Document
from app.modules.matters.models import Matter
from app.modules.tasks.models import Task


class ClientService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ClientRepository(db)
        self.contact_repo = ClientContactRepository(db)
        self.service_repo = ClientServiceRepository(db)

    async def create(self, data: ClientCreate, tenant_id: UUID, created_by: UUID) -> Client:
        if data.pan:
            existing = await self.repository.get_by_pan(data.pan, tenant_id)
            if existing:
                raise ConflictException(detail="Client with this PAN already exists")
        if data.gstin:
            existing = await self.repository.get_by_gstin(data.gstin, tenant_id)
            if existing:
                raise ConflictException(detail="Client with this GSTIN already exists")

        client_data = data.model_dump()
        client = Client(**client_data, tenant_id=tenant_id, created_by=created_by)
        return await self.repository.create(client)

    async def get_by_id(self, client_id: UUID, tenant_id: UUID) -> Client:
        client = await self.repository.get_by_id(client_id, tenant_id)
        if not client:
            raise NotFoundException(detail="Client not found")
        return client

    async def get_overview(self, client_id: UUID, tenant_id: UUID) -> dict:
        client = await self.get_by_id(client_id, tenant_id)
        contacts = await self.contact_repo.get_by_client(client_id, tenant_id)
        services = await self.service_repo.get_by_client(client_id, tenant_id)

        matters_count = await self.db.scalar(
            select(func.count(Matter.id)).where(Matter.client_id == client_id, Matter.tenant_id == tenant_id)
        ) or 0
        active_matters_count = await self.db.scalar(
            select(func.count(Matter.id)).where(
                Matter.client_id == client_id, Matter.tenant_id == tenant_id, Matter.status.in_(["in_progress", "ready_for_review"])
            )
        ) or 0
        tasks_count = await self.db.scalar(
            select(func.count(Task.id)).where(Task.client_id == client_id, Task.tenant_id == tenant_id)
        ) or 0
        overdue_tasks_count = await self.db.scalar(
            select(func.count(Task.id)).where(
                Task.client_id == client_id, Task.tenant_id == tenant_id,
                Task.due_date < datetime.now(UTC), Task.status != "completed"
            )
        ) or 0
        documents_count = await self.db.scalar(
            select(func.count(Document.id)).where(Document.client_id == client_id, Document.tenant_id == tenant_id)
        ) or 0
        compliance_cycles_count = await self.db.scalar(
            select(func.count(ComplianceCycle.id)).where(ComplianceCycle.client_id == client_id, ComplianceCycle.tenant_id == tenant_id)
        ) or 0
        pending_compliance_count = await self.db.scalar(
            select(func.count(ComplianceCycle.id)).where(
                ComplianceCycle.client_id == client_id, ComplianceCycle.tenant_id == tenant_id,
                ComplianceCycle.status.in_(["pending", "in_progress"])
            )
        ) or 0
        invoices_count = await self.db.scalar(
            select(func.count(Invoice.id)).where(Invoice.client_id == client_id, Invoice.tenant_id == tenant_id)
        ) or 0
        pending_invoices_amount = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.balance_amount), 0)).where(
                Invoice.client_id == client_id, Invoice.tenant_id == tenant_id,
                Invoice.status.in_(["sent", "partial", "overdue"])
            )
        ) or 0.0

        return {
            "client": client,
            "contacts": contacts,
            "services": services,
            "matters_count": matters_count,
            "active_matters_count": active_matters_count,
            "tasks_count": tasks_count,
            "overdue_tasks_count": overdue_tasks_count,
            "documents_count": documents_count,
            "compliance_cycles_count": compliance_cycles_count,
            "pending_compliance_count": pending_compliance_count,
            "invoices_count": invoices_count,
            "pending_invoices_amount": pending_invoices_amount,
            "recent_activity": [],
        }

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        category: ClientCategory | None = None,
        status: ClientStatus | None = None,
        responsible_user_id: UUID | None = None,
        responsible_team_id: UUID | None = None,
        is_archived: bool = False,
        tags: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Client], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, category, status,
            responsible_user_id, responsible_team_id, is_archived, tags, sort_by, sort_order
        )

    async def update(self, client_id: UUID, tenant_id: UUID, data: ClientUpdate, updated_by: UUID) -> Client:
        client = await self.get_by_id(client_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("pan"):
            existing = await self.repository.get_by_pan(update_data["pan"], tenant_id)
            if existing and existing.id != client_id:
                raise ConflictException(detail="Client with this PAN already exists")
        if update_data.get("gstin"):
            existing = await self.repository.get_by_gstin(update_data["gstin"], tenant_id)
            if existing and existing.id != client_id:
                raise ConflictException(detail="Client with this GSTIN already exists")

        for field, value in update_data.items():
            setattr(client, field, value)
        client.updated_by = updated_by
        return await self.repository.update(client)

    async def delete(self, client_id: UUID, tenant_id: UUID) -> None:
        client = await self.get_by_id(client_id, tenant_id)
        await self.repository.delete(client)

    async def archive(self, client_id: UUID, tenant_id: UUID, archived_by: UUID) -> Client:
        client = await self.get_by_id(client_id, tenant_id)
        return await self.repository.archive(client, archived_by)

    async def unarchive(self, client_id: UUID, tenant_id: UUID) -> Client:
        client = await self.get_by_id(client_id, tenant_id)
        return await self.repository.unarchive(client)


class ClientContactService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ClientContactRepository(db)

    async def create(self, client_id: UUID, tenant_id: UUID, data: ContactCreate, created_by: UUID) -> ClientContact:
        contact = ClientContact(
            client_id=client_id,
            tenant_id=tenant_id,
            created_by=created_by,
            **data.model_dump(),
        )
        if contact.is_primary:
            await self._unset_primary(client_id, tenant_id)
        return await self.repo.create(contact)

    async def get_by_id(self, contact_id: UUID, tenant_id: UUID) -> ClientContact:
        contact = await self.repo.get_by_id(contact_id, tenant_id)
        if not contact:
            raise NotFoundException(detail="Contact not found")
        return contact

    async def get_by_client(self, client_id: UUID, tenant_id: UUID) -> list[ClientContact]:
        return await self.repo.get_by_client(client_id, tenant_id)

    async def update(self, contact_id: UUID, tenant_id: UUID, data: ContactUpdate, updated_by: UUID) -> ClientContact:
        contact = await self.get_by_id(contact_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("is_primary"):
            await self._unset_primary(contact.client_id, tenant_id, exclude_id=contact_id)

        for field, value in update_data.items():
            setattr(contact, field, value)
        contact.updated_by = updated_by
        return await self.repo.update(contact)

    async def delete(self, contact_id: UUID, tenant_id: UUID) -> None:
        contact = await self.get_by_id(contact_id, tenant_id)
        await self.repo.delete(contact)

    async def _unset_primary(self, client_id: UUID, tenant_id: UUID, exclude_id: UUID = None) -> None:
        query = select(ClientContact).where(
            ClientContact.client_id == client_id,
            ClientContact.tenant_id == tenant_id,
            ClientContact.is_primary == True,
        )
        if exclude_id:
            query = query.where(ClientContact.id != exclude_id)
        result = await self.db.execute(query)
        contacts = result.scalars().all()
        for c in contacts:
            c.is_primary = False
        await self.db.flush()


class ClientServiceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ClientServiceRepository(db)

    async def create(self, client_id: UUID, tenant_id: UUID, data: ServiceCreate, created_by: UUID) -> ClientService:
        existing = await self.repo.get_by_client_and_type(client_id, data.service_type, tenant_id)
        if existing:
            raise ConflictException(detail=f"Service of type '{data.service_type}' already exists for this client")

        service = ClientService(
            client_id=client_id,
            tenant_id=tenant_id,
            created_by=created_by,
            **data.model_dump(),
        )
        return await self.repo.create(service)

    async def get_by_id(self, service_id: UUID, tenant_id: UUID) -> ClientService:
        service = await self.repo.get_by_id(service_id, tenant_id)
        if not service:
            raise NotFoundException(detail="Service not found")
        return service

    async def get_by_client(self, client_id: UUID, tenant_id: UUID) -> list[ClientService]:
        return await self.repo.get_by_client(client_id, tenant_id)

    async def update(self, service_id: UUID, tenant_id: UUID, data: ServiceUpdate, updated_by: UUID) -> ClientService:
        service = await self.get_by_id(service_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if "service_type" in update_data:
            existing = await self.repo.get_by_client_and_type(service.client_id, update_data["service_type"], tenant_id)
            if existing and existing.id != service_id:
                raise ConflictException(detail=f"Service of type '{update_data['service_type']}' already exists for this client")

        for field, value in update_data.items():
            setattr(service, field, value)
        service.updated_by = updated_by
        return await self.repo.update(service)

    async def delete(self, service_id: UUID, tenant_id: UUID) -> None:
        service = await self.get_by_id(service_id, tenant_id)
        await self.repo.delete(service)
