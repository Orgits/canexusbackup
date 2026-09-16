import hmac
import hashlib
import json
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.webhooks.models import WebhookEndpoint, WebhookEvent
from app.modules.webhooks.repository import WebhookRepository
from app.modules.webhooks.schemas import (
    WebhookEndpointCreate,
    WebhookEndpointUpdate,
    WebhookEventCreate,
)
from app.modules.users.models import User


class WebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = WebhookRepository(db)

    async def create_endpoint(self, data: WebhookEndpointCreate, tenant_id: UUID, created_by: UUID) -> WebhookEndpoint:
        # Check for duplicate URL
        existing = await self.repository.get_endpoint_by_url(data.url, tenant_id)
        if existing:
            raise ValueError("Webhook endpoint with this URL already exists")

        endpoint = WebhookEndpoint(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by_id=created_by,
        )
        return await self.repository.create_endpoint(endpoint)

    async def get_endpoint(self, endpoint_id: UUID, tenant_id: UUID) -> WebhookEndpoint:
        endpoint = await self.repository.get_endpoint_by_id(endpoint_id, tenant_id)
        if not endpoint:
            raise NotFoundException(detail="Webhook endpoint not found")
        return endpoint

    async def get_endpoint_by_url(self, url: str, tenant_id: UUID) -> WebhookEndpoint | None:
        return await self.repository.get_endpoint_by_url(url, tenant_id)

    async def list_endpoints(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list, int]:
        return await self.repository.get_all_endpoints(tenant_id, page, page_size, is_active, search)

    async def update_endpoint(self, endpoint_id: UUID, tenant_id: UUID, data: dict, updated_by: UUID) -> WebhookEndpoint:
        endpoint = await self.get_endpoint(endpoint_id, tenant_id)

        for field, value in data.items():
            if hasattr(endpoint, field):
                setattr(endpoint, field, value)

        return await self.repository.update_endpoint(endpoint)

    async def delete_endpoint(self, endpoint_id: UUID, tenant_id: UUID) -> None:
        endpoint = await self.get_endpoint(endpoint_id, tenant_id)
        await self.repository.delete_endpoint(endpoint)

    async def toggle_endpoint(self, endpoint_id: UUID, tenant_id: UUID, is_active: bool) -> WebhookEndpoint:
        endpoint = await self.get_endpoint(endpoint_id, tenant_id)
        endpoint.is_active = is_active
        return await self.repository.update_endpoint(endpoint)

    async def get_endpoint_stats(self, tenant_id: UUID) -> dict:
        return await self.repository.get_endpoint_stats(tenant_id)

    async def receive_event(
        self,
        tenant_id: UUID,
        endpoint: WebhookEndpoint,
        payload: dict,
        headers: dict,
        query_params: dict,
        source: str,
    ) -> WebhookEvent:
        # Generate idempotency key
        idempotency_key = headers.get("x-idempotency-key") or headers.get("x-request-id")

        # Check for duplicate
        if idempotency_key:
            existing = await self.repository.get_event_by_idempotency_key(headers.get("x-idempotency-key"), tenant_id)
            if existing:
                return existing

        # Create event
        event = WebhookEvent(
            source=endpoint.name,  # Use endpoint name as source
            external_id=headers.get("x-message-id") or headers.get("x-message-id") or "",
            event_type="",
            event_category="",
            payload=payload,
            raw_payload=json.dumps(payload),
            headers=headers,
            query_params=query_params,
            idempotency_key=idempotency_key,
            tenant_id=tenant_id,
            status="received",
        )
        return await self.repository.create_event(event)

    async def process_event(self, event: WebhookEvent, handler) -> WebhookEvent:
        event.status = "processing"
        event.processing_attempts += 1
        event.last_attempt_at = datetime.now()
        await self.db.flush()

        try:
            await handler(event)
            event.status = "processed"
            event.processed_at = datetime.now()
        except Exception as e:
            event.last_error = str(e)
            if event.processing_attempts >= event.max_attempts:
                event.status = "dlq"
            else:
                event.status = "retry"
                event.retry_after = datetime.now() + timedelta(minutes=5 * event.processing_attempts)

            event.last_attempt_at = datetime.now()
            await self.db.flush()
            raise

        event.last_attempt_at = datetime.now()
        await self.db.flush()
        return event

    async def retry_failed_events(self, tenant_id: UUID, max_events: int = 100) -> int:
        from sqlalchemy import select
        from app.modules.webhooks.models import WebhookEvent

        result = await self.db.execute(
            select(WebhookEvent).where(
                WebhookEvent.tenant_id == tenant_id,
                WebhookEvent.status.in_(["failed", "retry"]),
                WebhookEvent.retry_after <= datetime.now(),
            ).limit(max_events)
        )
        events = result.scalars().all()

        retried = 0
        for event in events:
            event.status = "retry"
            event.processing_attempts = 0
            event.last_error = None
            retried += 1

        await self.db.flush()
        return retried

    async def get_endpoint_stats(self, tenant_id: UUID) -> dict:
        return await self.repository.get_endpoint_stats(tenant_id)

    async def get_event_stats(self, tenant_id: UUID) -> dict:
        return await self.repository.get_event_stats(tenant_id)