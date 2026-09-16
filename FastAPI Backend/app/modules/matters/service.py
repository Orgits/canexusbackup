from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.clients.models import Client
from app.modules.matters.models import Matter, MatterPriority, MatterStatus, MatterType
from app.modules.matters.repository import MatterRepository
from app.modules.matters.schemas import MatterCreate, MatterStatusTransition, MatterUpdate
from app.modules.users.models import Team, User


class MatterService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = MatterRepository(db)

    async def create(self, data: MatterCreate, tenant_id: UUID, created_by: UUID) -> Matter:
        if data.matter_number:
            existing = await self.repository.get_by_number(data.matter_number, tenant_id)
            if existing:
                raise ConflictException(detail="Matter with this number already exists")

        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        client = client_result.scalar_one_or_none()
        if not client:
            raise NotFoundException(detail="Client not found")

        if data.responsible_user_id:
            user_result = await self.db.execute(
                select(User).where(User.id == data.responsible_user_id, User.tenant_id == tenant_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise NotFoundException(detail="Responsible user not found")

        if data.responsible_team_id:
            team_result = await self.db.execute(
                select(Team).where(Team.id == data.responsible_team_id, Team.tenant_id == tenant_id)
            )
            team = team_result.scalar_one_or_none()
            if not team:
                raise NotFoundException(detail="Responsible team not found")

        matter = Matter(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=MatterStatus.CREATED,
        )
        return await self.repository.create(matter)

    async def get_by_id(self, matter_id: UUID, tenant_id: UUID) -> Matter:
        matter = await self.repository.get_by_id(matter_id, tenant_id)
        if not matter:
            raise NotFoundException(detail="Matter not found")
        return matter

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_type: MatterType | None = None,
        status: MatterStatus | None = None,
        priority: MatterPriority | None = None,
        responsible_user_id: UUID | None = None,
        responsible_team_id: UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        tags: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Matter], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, matter_type,
            status, priority, responsible_user_id, responsible_team_id,
            due_date_from, due_date_to, tags, sort_by, sort_order
        )

    async def update(self, matter_id: UUID, tenant_id: UUID, data: MatterUpdate, updated_by: UUID) -> Matter:
        matter = await self.get_by_id(matter_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("matter_number"):
            existing = await self.repository.get_by_number(update_data["matter_number"], tenant_id)
            if existing and existing.id != matter_id:
                raise ConflictException(detail="Matter with this number already exists")

        if update_data.get("responsible_user_id"):
            user_result = await self.db.execute(
                select(User).where(User.id == update_data["responsible_user_id"], User.tenant_id == tenant_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise NotFoundException(detail="Responsible user not found")

        if update_data.get("responsible_team_id"):
            team_result = await self.db.execute(
                select(Team).where(Team.id == update_data["responsible_team_id"], Team.tenant_id == tenant_id)
            )
            team = team_result.scalar_one_or_none()
            if not team:
                raise NotFoundException(detail="Responsible team not found")

        if update_data.get("client_id"):
            client_result = await self.db.execute(
                select(Client).where(Client.id == update_data["client_id"], Client.tenant_id == tenant_id)
            )
            client = client_result.scalar_one_or_none()
            if not client:
                raise NotFoundException(detail="Client not found")

        for field, value in update_data.items():
            setattr(matter, field, value)
        matter.updated_by = updated_by
        return await self.repository.update(matter)

    async def transition_status(self, matter_id: UUID, tenant_id: UUID, data: MatterStatusTransition, updated_by: UUID) -> Matter:
        matter = await self.get_by_id(matter_id, tenant_id)
        valid_transitions = {
            MatterStatus.CREATED: [MatterStatus.INFORMATION_PENDING, MatterStatus.IN_PROGRESS],
            MatterStatus.INFORMATION_PENDING: [MatterStatus.IN_PROGRESS, MatterStatus.CLOSED],
            MatterStatus.IN_PROGRESS: [MatterStatus.READY_FOR_REVIEW, MatterStatus.INFORMATION_PENDING, MatterStatus.REWORK],
            MatterStatus.READY_FOR_REVIEW: [MatterStatus.APPROVED, MatterStatus.REWORK, MatterStatus.IN_PROGRESS],
            MatterStatus.REWORK: [MatterStatus.IN_PROGRESS, MatterStatus.READY_FOR_REVIEW],
            MatterStatus.APPROVED: [MatterStatus.FILED, MatterStatus.REWORK],
            MatterStatus.FILED: [MatterStatus.BILLING_FOLLOWUP, MatterStatus.CLOSED],
            MatterStatus.BILLING_FOLLOWUP: [MatterStatus.CLOSED],
            MatterStatus.CLOSED: [],
        }

        if data.status not in valid_transitions.get(matter.status, []):
            raise ConflictException(detail=f"Invalid status transition from {matter.status} to {data.status}")

        matter.status = data.status
        matter.updated_by = updated_by

        if data.status == MatterStatus.FILED:
            matter.completed_date = datetime.now(UTC)
            matter.progress_percentage = 100
        elif data.status == MatterStatus.CLOSED:
            matter.completed_date = datetime.now(UTC)

        return await self.repository.update(matter)

    async def delete(self, matter_id: UUID, tenant_id: UUID) -> None:
        matter = await self.get_by_id(matter_id, tenant_id)
        await self.repository.delete(matter)
