from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.mfa.models import MFAEnrollment, MFAVerificationLog, MFALoginChallenge, MFAEnrollmentStatus, MFAMethod


class MFAEnrollmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, enrollment: MFAEnrollment) -> MFAEnrollment:
        self.db.add(enrollment)
        await self.db.flush()
        await self.db.refresh(enrollment)
        return enrollment

    async def get_by_id(self, enrollment_id: UUID, tenant_id: UUID) -> MFAEnrollment | None:
        result = await self.db.execute(
            select(MFAEnrollment)
            .options(
                selectinload(MFAEnrollment.user),
                selectinload(MFAEnrollment.disabled_by),
            )
            .where(MFAEnrollment.id == enrollment_id, MFAEnrollment.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID, tenant_id: UUID) -> MFAEnrollment | None:
        result = await self.db.execute(
            select(MFAEnrollment).where(
                MFAEnrollment.user_id == user_id,
                MFAEnrollment.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_method(self, user_id: UUID, method: MFAMethod, tenant_id: UUID) -> MFAEnrollment | None:
        result = await self.db.execute(
            select(MFAEnrollment).where(
                MFAEnrollment.user_id == user_id,
                MFAEnrollment.method == method,
                MFAEnrollment.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, enrollment: MFAEnrollment) -> MFAEnrollment:
        await self.db.flush()
        await self.db.refresh(enrollment)
        return enrollment

    async def delete(self, enrollment: MFAEnrollment) -> None:
        await self.db.delete(enrollment)
        await self.db.flush()


class MFAVerificationLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: MFAVerificationLog) -> MFAVerificationLog:
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        enrollment_id: UUID | None = None,
        user_id: UUID | None = None,
        method: str | None = None,
        result: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[MFAVerificationLog], int]:
        query = select(MFAVerificationLog).where(MFAVerificationLog.tenant_id == tenant_id)
        count_query = select(func.count(MFAVerificationLog.id)).where(MFAVerificationLog.tenant_id == tenant_id)

        if enrollment_id:
            query = query.where(MFAVerificationLog.enrollment_id == enrollment_id)
            count_query = count_query.where(MFAVerificationLog.enrollment_id == enrollment_id)

        if user_id:
            query = query.where(MFAVerificationLog.user_id == user_id)
            count_query = count_query.where(MFAVerificationLog.user_id == user_id)

        if method:
            query = query.where(MFAVerificationLog.method == method)
            count_query = count_query.where(MFAVerificationLog.method == method)

        if result:
            query = query.where(MFAVerificationLog.result == result)
            count_query = count_query.where(MFAVerificationLog.result == result)

        if date_from:
            query = query.where(MFAVerificationLog.created_at >= date_from)
            count_query = count_query.where(MFAVerificationLog.created_at >= date_from)

        if date_to:
            query = query.where(MFAVerificationLog.created_at <= date_to)
            count_query = count_query.where(MFAVerificationLog.created_at <= date_to)

        sort_column = getattr(MFAVerificationLog, sort_by, MFAVerificationLog.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(MFAVerificationLog.enrollment),
                selectinload(MFAVerificationLog.user),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0


class MFALoginChallengeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, challenge: MFALoginChallenge) -> MFALoginChallenge:
        self.db.add(challenge)
        await self.db.flush()
        await self.db.refresh(challenge)
        return challenge

    async def get_by_challenge_id(self, challenge_id: str, tenant_id: UUID) -> MFALoginChallenge | None:
        result = await self.db.execute(
            select(MFALoginChallenge).where(
                MFALoginChallenge.challenge_id == challenge_id,
                MFALoginChallenge.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID, tenant_id: UUID) -> list[MFALoginChallenge]:
        result = await self.db.execute(
            select(MFALoginChallenge)
            .where(
                MFALoginChallenge.user_id == user_id,
                MFALoginChallenge.tenant_id == tenant_id,
            )
            .order_by(MFALoginChallenge.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, challenge: MFALoginChallenge) -> MFALoginChallenge:
        await self.db.flush()
        await self.db.refresh(challenge)
        return challenge

    async def cleanup_expired(self, tenant_id: UUID) -> int:
        result = await self.db.execute(
            delete(MFALoginChallenge).where(
                MFALoginChallenge.tenant_id == tenant_id,
                MFALoginChallenge.expires_at < datetime.utcnow(),
                MFALoginChallenge.status == "pending",
            )
        )
        return result.rowcount