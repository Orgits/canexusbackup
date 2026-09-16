from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.webhooks.models import WebhookEndpoint, WebhookEvent


class WebhookRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        self.db.add(endpoint)
        await self.db.flush()
        await self.db.refresh(endpoint)
        return endpoint

    async def get_endpoint_by_id(self, endpoint_id: UUID, tenant_id: UUID) -> WebhookEndpoint | None:
        result = await self.db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_endpoint_by_url(self, url: str, tenant_id: UUID) -> WebhookEndpoint | None:
        result = await self.db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.url == url, WebhookEndpoint.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all_endpoints(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[WebhookEndpoint], int]:
        query = select(WebhookEndpoint).where(WebhookEndpoint.tenant_id == tenant_id)
        count_query = select(func.count(WebhookEndpoint.id)).where(WebhookEndpoint.tenant_id == tenant_id)

        if is_active is not None:
            query = query.where(WebhookEndpoint.is_active == is_active)
            count_query = count_query.where(WebhookEndpoint.is_active == is_active)

        if search:
            search_filter = (
                WebhookEndpoint.name.ilike(f"%{search}%") |
                WebhookEndpoint.url.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(WebhookEndpoint.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create_event(self, event: WebhookEvent) -> WebhookEvent:
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_event_by_id(self, event_id: UUID, tenant_id: UUID) -> WebhookEvent | None:
        result = await self.db.execute(
            select(WebhookEvent).where(WebhookEvent.id == event_id, WebhookEvent.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_event_by_idempotency_key(self, idempotency_key: str, tenant_id: UUID) -> WebhookEvent | None:
        result = await self.db.execute(
            select(WebhookEvent).where(
                WebhookEvent.idempotency_key == idempotency_key,
                WebhookEvent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_events(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        source: str | None = None,
        status: str | None = None,
        event_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[WebhookEvent], int]:
        from sqlalchemy import func, or_, select

        query = select(WebhookEvent).where(WebhookEvent.tenant_id == tenant_id)
        count_query = select(func.count(WebhookEvent.id)).where(WebhookEvent.tenant_id == tenant_id)

        if source:
            query = query.where(WebhookEvent.source == source)
            count_query = count_query.where(WebhookEvent.source == source)

        if status:
            query = query.where(WebhookEvent.status == status)
            count_query = count_query.where(WebhookEvent.status == status)

        if event_type:
            query = query.where(WebhookEvent.event_type == event_type)
            count_query = count_query.where(WebhookEvent.event_type == event_type)

        if date_from:
            query = query.where(WebhookEvent.created_at >= date_from)
            count_query = count_query.where(WebhookEvent.created_at >= date_from)

        if date_to:
            query = query.where(WebhookEvent.created_at <= date_to)
            count_query = count_query.where(WebhookEvent.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(WebhookEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        await self.db.flush()
        await self.db.refresh(endpoint)
        return endpoint

    async def update_event(self, event: WebhookEvent) -> WebhookEvent:
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete_endpoint(self, endpoint: WebhookEndpoint) -> None:
        await self.db.delete(endpoint)
        await self.db.flush()

    async def get_endpoint_stats(self, tenant_id: UUID) -> dict:
        from sqlalchemy import func
        result = await self.db.execute(
            select(
                func.count(WebhookEndpoint.id).label("total"),
                func.count(WebhookEndpoint.id).filter(WebhookEndpoint.is_active == True).label("active"),
                func.count(WebhookEndpoint.id).filter(WebhookEndpoint.is_active == False).label("inactive"),
            ).where(WebhookEndpoint.tenant_id == tenant_id)
        )
        stats = result.first()
        return {
            "total": stats.total,
            "active": stats.active,
            "inactive": stats.inactive,
        }

    async def get_event_stats(self, tenant_id: UUID) -> dict:
        from sqlalchemy import func
        result = await self.db.execute(
            select(
                func.count(WebhookEvent.id).label("total"),
                func.count(WebhookEvent.id).filter(WebhookEvent.status == "processed").label("processed"),
                func.count(WebhookEvent.id).filter(WebhookEvent.status == "failed").label("failed"),
                func.count(WebhookEvent.id).filter(WebhookEvent.status == "retry").label("retry"),
                func.count(WebhookEvent.id).filter(WebhookEvent.status == "dlq").label("dlq"),
            ).where(WebhookEvent.tenant_id == tenant_id)
        )
        stats = result.first()
        return {
            "total": stats.total,
            "processed": stats.processed,
            "failed": stats.failed,
            "retry": stats.retry,
            "dlq": stats.dlq,
        }