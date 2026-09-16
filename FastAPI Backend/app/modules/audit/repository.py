from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.models import AuditAction, AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, audit_log: AuditLog) -> AuditLog:
        self.db.add(audit_log)
        await self.db.flush()
        await self.db.refresh(audit_log)
        return audit_log

    async def get_by_id(self, log_id: UUID, tenant_id: UUID) -> AuditLog | None:
        result = await self.db.execute(
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(AuditLog.id == log_id, AuditLog.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        user_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        start_from: datetime | None = None,
        start_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[AuditLog], int]:
        query = (
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(AuditLog.tenant_id == tenant_id)
        )
        count_query = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant_id)

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)

        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)

        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            count_query = count_query.where(AuditLog.resource_type == resource_type)

        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
            count_query = count_query.where(AuditLog.resource_id == resource_id)

        if start_from:
            query = query.where(AuditLog.created_at >= start_from)
            count_query = count_query.where(AuditLog.created_at >= start_from)

        if start_to:
            query = query.where(AuditLog.created_at <= start_to)
            count_query = count_query.where(AuditLog.created_at <= start_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(AuditLog, sort_by):
            sort_column = getattr(AuditLog, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(AuditLog.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total
