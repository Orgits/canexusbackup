from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.outbox.models import OutboxEvent, OutboxEventType
from app.modules.outbox.repository import OutboxRepository


class OutboxService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OutboxRepository(db)

    async def emit_event(
        self,
        tenant_id: UUID,
        event_type: OutboxEventType,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict,
        idempotency_key: str | None = None,
        max_retries: int = 5,
    ) -> OutboxEvent:
        if idempotency_key:
            existing = await self.repository.get_by_idempotency_key(tenant_id, idempotency_key)
            if existing:
                return existing

        event = await self.repository.create_event(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            idempotency_key=idempotency_key,
            max_retries=max_retries,
        )
        return event

    async def emit_events_batch(
        self,
        tenant_id: UUID,
        events: list[dict],
    ) -> list[OutboxEvent]:
        created = []
        for event_data in events:
            event = await self.emit_event(
                tenant_id=tenant_id,
                event_type=event_data["event_type"],
                aggregate_type=event_data["aggregate_type"],
                aggregate_id=event_data["aggregate_id"],
                payload=event_data["payload"],
                idempotency_key=event_data.get("idempotency_key"),
                max_retries=event_data.get("max_retries", 5),
            )
            created.append(event)
        return created


def get_outbox_service(db: AsyncSession) -> OutboxService:
    return OutboxService(db)
