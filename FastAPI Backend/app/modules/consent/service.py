from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.clients.models import Client
from app.modules.consent.models import Consent, ConsentTemplate, ConsentStatus, ConsentChannel
from app.modules.consent.repository import ConsentRepository
from app.modules.consent.schemas import ConsentCreate, ConsentUpdate, ConsentTemplateCreate, ConsentTemplateUpdate
from app.modules.users.models import User


class ConsentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ConsentRepository(db)

    async def create(self, data: ConsentCreate, tenant_id: UUID, created_by: UUID) -> Consent:
        # Validate client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        # Check for existing consent for same client and channel
        existing = await self.repository.get_by_client_and_channel(data.client_id, data.channel, tenant_id)
        if existing:
            raise ValueError(f"Consent for client {data.client_id} and channel {data.channel} already exists")

        consent = Consent(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create(consent)

    async def get_by_id(self, consent_id: UUID, tenant_id: UUID) -> Consent:
        consent = await self.repository.get_by_id(consent_id, tenant_id)
        if not consent:
            raise NotFoundException(detail="Consent not found")
        return consent

    async def get_by_client_and_channel(self, client_id: UUID, channel: str, tenant_id: UUID) -> Consent | None:
        return await self.repository.get_by_client_and_channel(client_id, channel, tenant_id)

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        channel: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Consent], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, channel, status, date_from, date_to, sort_by, sort_order
        )

    async def update(self, consent_id: UUID, tenant_id: UUID, data: ConsentUpdate, updated_by: UUID) -> Consent:
        consent = await self.get_by_id(consent_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status changes
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == ConsentStatus.WITHDRAWN and consent.status != ConsentStatus.WITHDRAWN:
                consent.withdrawn_at = datetime.now()
            elif new_status == ConsentStatus.GIVEN and consent.status != ConsentStatus.GIVEN:
                consent.given_at = datetime.now()

        for field, value in update_data.items():
            setattr(consent, field, value)

        consent.updated_at = datetime.now()
        return await self.repository.update(consent)

    async def withdraw(self, consent_id: UUID, tenant_id: UUID, withdrawn_by: UUID) -> Consent:
        consent = await self.get_by_id(consent_id, tenant_id)
        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawn_at = datetime.now()
        consent.updated_at = datetime.now()
        return await self.repository.update(consent)

    async def get_all_templates(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        channel: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[ConsentTemplate], int]:
        return await self.repository.get_all_templates(tenant_id, page, page_size, channel, is_active)

    async def get_template_by_id(self, template_id: UUID, tenant_id: UUID) -> ConsentTemplate:
        template = await self.repository.get_template_by_id(template_id, tenant_id)
        if not template:
            raise NotFoundException(detail="Consent template not found")
        return template

    async def get_template_by_channel(self, channel: str, tenant_id: UUID) -> ConsentTemplate | None:
        return await self.repository.get_template_by_channel(channel, tenant_id)

    async def create_template(self, data: ConsentTemplateCreate, tenant_id: UUID, created_by: UUID) -> ConsentTemplate:
        # Check if default template for channel already exists
        if data.is_default:
            existing = await self.db.execute(
                select(ConsentTemplate).where(
                    ConsentTemplate.channel == data.channel,
                    ConsentTemplate.tenant_id == tenant_id,
                    ConsentTemplate.is_default == True,
                    ConsentTemplate.is_active == True,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Default template for channel {data.channel} already exists")

        template = ConsentTemplate(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by_id=created_by,
        )
        return await self.repository.create_template(template)

    async def update_template(self, template_id: UUID, tenant_id: UUID, data: ConsentTemplateUpdate, updated_by: UUID) -> ConsentTemplate:
        template = await self.get_template_by_id(template_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_at = datetime.now()
        return await self.repository.update(template)

    async def delete_template(self, template_id: UUID, tenant_id: UUID) -> None:
        template = await self.get_template_by_id(template_id, tenant_id)
        await self.repository.delete(template)

    async def set_default_template(self, template_id: UUID, tenant_id: UUID) -> ConsentTemplate:
        template = await self.get_template_by_id(template_id, tenant_id)

        # Unset current default
        await self.db.execute(
            select(ConsentTemplate).where(
                ConsentTemplate.channel == template.channel,
                ConsentTemplate.tenant_id == tenant_id,
                ConsentTemplate.is_default == True,
            )
        )
        result = await self.db.execute(
            select(ConsentTemplate).where(
                ConsentTemplate.channel == template.channel,
                ConsentTemplate.tenant_id == tenant_id,
                ConsentTemplate.is_default == True,
            )
        )
        current_default = result.scalar_one_or_none()
        if current_default:
            current_default.is_default = False

        template.is_default = True
        await self.db.flush()
        await self.db.refresh(template)

        return template