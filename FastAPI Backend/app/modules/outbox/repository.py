from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.outbox.models import OutboxEvent, OutboxEventType, OutboxStatus


class OutboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(
        self,
        tenant_id: UUID,
        event_type: OutboxEventType,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict,
        idempotency_key: str | None = None,
        max_retries: int = 5,
    ) -> OutboxEvent:
        event = OutboxEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            idempotency_key=idempotency_key,
            max_retries=max_retries,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_pending_events(
        self, tenant_id: UUID, limit: int = 100
    ) -> list[OutboxEvent]:
        result = await self.db.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.tenant_id == tenant_id,
                OutboxEvent.status == OutboxStatus.PENDING,
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_events_for_processing(
        self, limit: int = 100
    ) -> list[OutboxEvent]:
        result = await self.db.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.status.in_([OutboxStatus.PENDING, OutboxStatus.FAILED]),
                OutboxEvent.retry_count < OutboxEvent.max_retries,
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_processing(self, event_id: UUID) -> bool:
        result = await self.db.execute(
            update(OutboxEvent)
            .where(
                OutboxEvent.id == event_id,
                OutboxEvent.status.in_([OutboxStatus.PENDING, OutboxStatus.FAILED]),
            )
            .values(
                status=OutboxStatus.PROCESSING,
                last_attempt_at=datetime.now(UTC),
            )
        )
        return result.rowcount > 0

    async def mark_processed(self, event_id: UUID) -> bool:
        result = await self.db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status=OutboxStatus.PROCESSED,
                processed_at=datetime.now(UTC),
            )
        )
        return result.rowcount > 0

    async def mark_failed(self, event_id: UUID, error: str) -> bool:
        result = await self.db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status=OutboxStatus.FAILED,
                retry_count=OutboxEvent.retry_count + 1,
                last_error=error,
                last_attempt_at=datetime.now(UTC),
            )
        )
        return result.rowcount > 0

    async def mark_dead_letter(self, event_id: UUID, error: str) -> bool:
        result = await self.db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status=OutboxStatus.DEAD_LETTER,
                last_error=error,
                last_attempt_at=datetime.now(UTC),
            )
        )
        return result.rowcount > 0

    async def get_by_idempotency_key(
        self, tenant_id: UUID, idempotency_key: str
    ) -> OutboxEvent | None:
        result = await self.db.execute(
            select(OutboxEvent).where(
                OutboxEvent.tenant_id == tenant_id,
                OutboxEvent.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def count_pending(self, tenant_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(OutboxEvent.id)).where(
                OutboxEvent.tenant_id == tenant_id,
                OutboxEvent.status == OutboxStatus.PENDING,
            )
        )
        return result.scalar() or 0

    async def cleanup_processed(
        self, tenant_id: UUID, older_than_days: int = 30
    ) -> int:
        cutoff = datetime.now(UTC) - datetime.timedelta(days=older_than_days)
        result = await self.db.execute(
            select(OutboxEvent.id).where(
                OutboxEvent.tenant_id == tenant_id,
                OutboxEvent.status == OutboxStatus.PROCESSED,
                OutboxEvent.processed_at < cutoff,
            )
        )
        ids = [row[0] for row in result.fetchall()]
        if ids:
            from sqlalchemy import delete
            await self.db.execute(
                delete(OutboxEvent).where(OutboxEvent.id.in_(ids))
            )
        return len(ids)
