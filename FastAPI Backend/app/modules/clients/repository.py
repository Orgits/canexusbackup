from datetime import UTC
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.clients.models import Client, ClientCategory, ClientContact, ClientService, ClientStatus


class ClientRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, client: Client) -> Client:
        self.db.add(client)
        await self.db.flush()
        await self.db.refresh(client)
        return client

    async def get_by_id(self, client_id: UUID, tenant_id: UUID) -> Client | None:
        result = await self.db.execute(
            select(Client)
            .options(
                selectinload(Client.contacts),
                selectinload(Client.services),
                selectinload(Client.responsible_user),
                selectinload(Client.responsible_team),
            )
            .where(Client.id == client_id, Client.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_pan(self, pan: str, tenant_id: UUID) -> Client | None:
        result = await self.db.execute(
            select(Client).where(Client.pan == pan, Client.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_gstin(self, gstin: str, tenant_id: UUID) -> Client | None:
        result = await self.db.execute(
            select(Client).where(Client.gstin == gstin, Client.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

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
        query = (
            select(Client)
            .options(
                selectinload(Client.responsible_user),
                selectinload(Client.responsible_team),
            )
            .where(Client.tenant_id == tenant_id, Client.is_archived == is_archived)
        )
        count_query = select(func.count(Client.id)).where(Client.tenant_id == tenant_id, Client.is_archived == is_archived)

        if search:
            search_filter = or_(
                Client.name.ilike(f"%{search}%"),
                Client.display_name.ilike(f"%{search}%"),
                Client.pan.ilike(f"%{search}%"),
                Client.gstin.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%"),
                Client.phone.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if category:
            query = query.where(Client.category == category)
            count_query = count_query.where(Client.category == category)

        if status:
            query = query.where(Client.status == status)
            count_query = count_query.where(Client.status == status)

        if responsible_user_id:
            query = query.where(Client.responsible_user_id == responsible_user_id)
            count_query = count_query.where(Client.responsible_user_id == responsible_user_id)

        if responsible_team_id:
            query = query.where(Client.responsible_team_id == responsible_team_id)
            count_query = count_query.where(Client.responsible_team_id == responsible_team_id)

        if tags:
            query = query.where(Client.tags.contains(tags))
            count_query = count_query.where(Client.tags.contains(tags))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Client, sort_by):
            sort_column = getattr(Client, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Client.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, client: Client) -> Client:
        await self.db.flush()
        await self.db.refresh(client)
        return client

    async def delete(self, client: Client) -> None:
        await self.db.delete(client)
        await self.db.flush()

    async def archive(self, client: Client, archived_by: UUID) -> Client:
        from datetime import datetime
        client.is_archived = True
        client.archived_at = datetime.now(UTC)
        client.archived_by = archived_by
        client.status = ClientStatus.ARCHIVED
        return await self.update(client)

    async def unarchive(self, client: Client) -> Client:
        client.is_archived = False
        client.archived_at = None
        client.archived_by = None
        client.status = ClientStatus.ACTIVE
        return await self.update(client)


class ClientContactRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, contact: ClientContact) -> ClientContact:
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)
        return contact

    async def get_by_id(self, contact_id: UUID, tenant_id: UUID) -> ClientContact | None:
        result = await self.db.execute(
            select(ClientContact).where(ClientContact.id == contact_id, ClientContact.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_client(self, client_id: UUID, tenant_id: UUID) -> list[ClientContact]:
        result = await self.db.execute(
            select(ClientContact)
            .where(ClientContact.client_id == client_id, ClientContact.tenant_id == tenant_id)
            .order_by(ClientContact.is_primary.desc(), ClientContact.created_at)
        )
        return list(result.scalars().all())

    async def update(self, contact: ClientContact) -> ClientContact:
        await self.db.flush()
        await self.db.refresh(contact)
        return contact

    async def delete(self, contact: ClientContact) -> None:
        await self.db.delete(contact)
        await self.db.flush()


class ClientServiceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, service: ClientService) -> ClientService:
        self.db.add(service)
        await self.db.flush()
        await self.db.refresh(service)
        return service

    async def get_by_id(self, service_id: UUID, tenant_id: UUID) -> ClientService | None:
        result = await self.db.execute(
            select(ClientService).where(ClientService.id == service_id, ClientService.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_client(self, client_id: UUID, tenant_id: UUID) -> list[ClientService]:
        result = await self.db.execute(
            select(ClientService)
            .where(ClientService.client_id == client_id, ClientService.tenant_id == tenant_id)
            .order_by(ClientService.created_at)
        )
        return list(result.scalars().all())

    async def get_by_client_and_type(self, client_id: UUID, service_type: str, tenant_id: UUID) -> ClientService | None:
        result = await self.db.execute(
            select(ClientService)
            .where(
                ClientService.client_id == client_id,
                ClientService.service_type == service_type,
                ClientService.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, service: ClientService) -> ClientService:
        await self.db.flush()
        await self.db.refresh(service)
        return service

    async def delete(self, service: ClientService) -> None:
        await self.db.delete(service)
        await self.db.flush()
