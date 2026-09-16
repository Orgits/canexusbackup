from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.channels.models import ChannelProvider, MessageLog, ProviderStatus


class ChannelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, provider: ChannelProvider) -> ChannelProvider:
        self.db.add(provider)
        await self.db.flush()
        await self.db.refresh(provider)
        return provider

    async def get_by_id(self, provider_id: UUID, tenant_id: UUID) -> ChannelProvider | None:
        result = await self.db.execute(
            select(ChannelProvider).where(ChannelProvider.id == provider_id, ChannelProvider.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_default(self, channel_type: str, tenant_id: UUID) -> ChannelProvider | None:
        result = await self.db.execute(
            select(ChannelProvider).where(
                ChannelProvider.channel_type == channel_type,
                ChannelProvider.tenant_id == tenant_id,
                ChannelProvider.is_default == True,
                ChannelProvider.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        channel_type: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[ChannelProvider], int]:
        query = select(ChannelProvider).where(ChannelProvider.tenant_id == tenant_id)
        count_query = select(func.count(ChannelProvider.id)).where(ChannelProvider.tenant_id == tenant_id)

        if channel_type:
            query = query.where(ChannelProvider.channel_type == channel_type)
            count_query = count_query.where(ChannelProvider.channel_type == channel_type)

        if status:
            query = query.where(ChannelProvider.status == status)
            count_query = count_query.where(ChannelProvider.status == status)

        if is_active is not None:
            query = query.where(ChannelProvider.is_active == is_active)
            count_query = count_query.where(ChannelProvider.is_active == is_active)

        if search:
            search_filter = ChannelProvider.name.ilike(f"%{search}%") | ChannelProvider.provider_name.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(ChannelProvider.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, provider: ChannelProvider) -> ChannelProvider:
        await self.db.flush()
        await self.db.refresh(provider)
        return provider

    async def delete(self, provider: ChannelProvider) -> None:
        await self.db.delete(provider)
        await self.db.flush()


class MessageLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: MessageLog) -> MessageLog:
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_by_id(self, log_id: UUID, tenant_id: UUID) -> MessageLog | None:
        result = await self.db.execute(
            select(MessageLog).where(MessageLog.id == log_id, MessageLog.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
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
    ) -> tuple[list[MessageLog], int]:
        from sqlalchemy import func, or_, select

        query = select(MessageLog).where(MessageLog.tenant_id == tenant_id)
        count_query = select(func.count(MessageLog.id)).where(MessageLog.tenant_id == tenant_id)

        if channel_type:
            query = query.where(MessageLog.channel_type == channel_type)
            count_query = count_query.where(MessageLog.channel_type == channel_type)

        if provider_id:
            query = query.where(MessageLog.provider_id == provider_id)
            count_query = count_query.where(MessageLog.provider_id == provider_id)

        if status:
            query = query.where(MessageLog.status == status)
            count_query = count_query.where(MessageLog.status == status)

        if recipient:
            query = query.where(MessageLog.recipient.ilike(f"%{recipient}%"))
            count_query = count_query.where(MessageLog.recipient.ilike(f"%{recipient}%"))

        if date_from:
            query = query.where(MessageLog.created_at >= date_from)
            count_query = count_query.where(MessageLog.created_at >= date_from)

        if date_to:
            query = query.where(MessageLog.created_at <= date_to)
            count_query = count_query.where(MessageLog.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(MessageLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, log: MessageLog) -> MessageLog:
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def delete(self, log: MessageLog) -> None:
        await self.db.delete(log)
        await self.db.flush()