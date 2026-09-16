from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.channels.models import ChannelProvider, MessageLog, ProviderStatus
from app.modules.channels.repository import ChannelRepository, MessageLogRepository
from app.modules.channels.schemas import ChannelProviderCreate, ChannelProviderUpdate, MessageLogCreate, SendMessageRequest
from app.modules.users.models import User


class ChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ChannelRepository(db)
        self.log_repository = MessageLogRepository(db)

    async def create_provider(self, data: ChannelProviderCreate, tenant_id: UUID, created_by: UUID) -> ChannelProvider:
        # Check if default already exists for this channel type
        if data.is_default:
            existing = await self.db.execute(
                select(ChannelProvider).where(
                    ChannelProvider.channel_type == data.channel_type,
                    ChannelProvider.tenant_id == tenant_id,
                    ChannelProvider.is_default == True,
                    ChannelProvider.is_active == True,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Default provider for channel type {data.channel_type} already exists")

        provider = ChannelProvider(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by_id=created_by,
            status=ProviderStatus.PENDING,
        )
        return await self.repository.create(provider)

    async def get_provider(self, provider_id: UUID, tenant_id: UUID) -> ChannelProvider:
        provider = await self.repository.get_by_id(provider_id, tenant_id)
        if not provider:
            raise NotFoundException(detail="Channel provider not found")
        return provider

    async def get_default_provider(self, channel_type: str, tenant_id: UUID) -> ChannelProvider:
        provider = await self.repository.get_default(channel_type, tenant_id)
        if not provider:
            raise NotFoundException(detail=f"No default provider configured for channel type {channel_type}")
        return provider

    async def list_providers(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        channel_type: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list, int]:
        return await self.repository.get_all(tenant_id, page, page_size, channel_type, status, is_active, search)

    async def update_provider(self, provider_id: UUID, tenant_id: UUID, data: dict, updated_by: UUID) -> ChannelProvider:
        provider = await self.get_provider(provider_id, tenant_id)

        for field, value in data.items():
            if hasattr(provider, field):
                setattr(provider, field, value)

        return await self.repository.update(provider)

    async def delete_provider(self, provider_id: UUID, tenant_id: UUID) -> None:
        provider = await self.get_provider(provider_id, tenant_id)
        await self.repository.delete(provider)

    async def set_default(self, provider_id: UUID, tenant_id: UUID) -> ChannelProvider:
        provider = await self.get_provider(provider_id, tenant_id)

        # Unset current default
        from sqlalchemy import select
        result = await self.db.execute(
            select(ChannelProvider).where(
                ChannelProvider.channel_type == provider.channel_type,
                ChannelProvider.tenant_id == tenant_id,
                ChannelProvider.is_default == True,
            )
        )
        current_default = result.scalars().first()
        if current_default:
            current_default.is_default = False

        provider.is_default = True
        return await self.repository.update(provider)

    async def test_provider(self, provider_id: UUID, tenant_id: UUID) -> dict:
        provider = await self.get_provider(provider_id, tenant_id)

        # TODO: Implement actual provider test based on channel type
        # This would connect to the provider's API and verify credentials

        provider.last_health_check = datetime.now()
        provider.error_count = 0
        provider.last_error = None
        provider.status = ProviderStatus.ACTIVE

        await self.db.flush()
        await self.db.refresh(provider)

        return {"status": "healthy", "provider": provider.name}


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = MessageLogRepository(db)

    async def send_message(self, data: SendMessageRequest, tenant_id: UUID, sent_by: UUID) -> MessageLog:
        # Get provider
        provider_result = await self.db.execute(
            select(ChannelProvider).where(
                ChannelProvider.id == data.provider_id,
                ChannelProvider.tenant_id == tenant_id,
            )
        )
        provider = provider_result.scalar_one_or_none()
        if not provider:
            raise NotFoundException(detail="Provider not found")

        if not provider.is_active:
            raise ValueError("Provider is not active")

        # Create message log
        log = MessageLog(
            provider_id=data.provider_id,
            channel_type=data.channel_type,
            direction="outbound",
            recipient=data.recipient,
            subject=data.subject,
            body=data.body,
            status="pending",
            scheduled_at=data.scheduled_at,
            tenant_id=tenant_id,
        )
        log = await self.log_repository.create(log)

        # TODO: Actually send message via provider
        # This would integrate with actual provider APIs (Twilio, SendGrid, WhatsApp Business API, etc.)

        # For now, mark as sent
        log.status = "sent"
        log.sent_at = datetime.now()
        log.provider_message_id = f"msg_{datetime.now().timestamp()}"

        await self.db.flush()
        await self.db.refresh(log)

        return log

    async def get_logs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        channel_type: str | None = None,
        provider_id: UUID | None = None,
        status: str | None = None,
        recipient: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.log_repository.get_all(
            tenant_id, page, page_size, channel_type, provider_id, status, recipient, date_from, date_to
        )

    async def get_log(self, log_id: UUID, tenant_id: UUID) -> MessageLog:
        log = await self.log_repository.get_by_id(log_id, tenant_id)
        if not log:
            raise NotFoundException(detail="Message log not found")
        return log

    async def retry_message(self, log_id: UUID, tenant_id: UUID) -> MessageLog:
        log = await self.get_log(log_id, tenant_id)

        if log.status not in ["failed", "bounced"]:
            raise ValueError("Can only retry failed or bounced messages")

        if log.retry_count >= log.max_retries:
            raise ValueError("Maximum retry attempts exceeded")

        log.status = "pending"
        log.retry_count += 1
        log.error_code = None
        log.error_message = None

        await self.db.flush()
        await self.db.refresh(log)

        return log