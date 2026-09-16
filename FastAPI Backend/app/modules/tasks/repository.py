from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.tasks.models import Task, TaskPriority, TaskStatus


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        result = await self.db.execute(
            select(Task)
            .options(
                selectinload(Task.client),
                selectinload(Task.matter),
                selectinload(Task.parent_task),
                selectinload(Task.assignee),
                selectinload(Task.team),
                selectinload(Task.reporter),
                selectinload(Task.source_communication),
            )
            .where(Task.id == task_id, Task.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, task_number: str, tenant_id: UUID) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.task_number == task_number, Task.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        team_id: UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        tags: list[str] | None = None,
        overdue_only: bool = False,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Task], int]:
        from datetime import datetime
        query = (
            select(Task)
            .options(
                selectinload(Task.client),
                selectinload(Task.matter),
                selectinload(Task.assignee),
                selectinload(Task.team),
            )
            .where(Task.tenant_id == tenant_id)
        )
        count_query = select(func.count(Task.id)).where(Task.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Task.title.ilike(f"%{search}%"),
                Task.task_number.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(Task.client_id == client_id)
            count_query = count_query.where(Task.client_id == client_id)

        if matter_id:
            query = query.where(Task.matter_id == matter_id)
            count_query = count_query.where(Task.matter_id == matter_id)

        if status:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)

        if priority:
            query = query.where(Task.priority == priority)
            count_query = count_query.where(Task.priority == priority)

        if assignee_id:
            query = query.where(Task.assignee_id == assignee_id)
            count_query = count_query.where(Task.assignee_id == assignee_id)

        if team_id:
            query = query.where(Task.team_id == team_id)
            count_query = count_query.where(Task.team_id == team_id)

        if due_date_from:
            query = query.where(Task.due_date >= due_date_from)
            count_query = count_query.where(Task.due_date >= due_date_from)

        if due_date_to:
            query = query.where(Task.due_date <= due_date_to)
            count_query = count_query.where(Task.due_date <= due_date_to)

        if tags:
            query = query.where(Task.tags.contains(tags))
            count_query = count_query.where(Task.tags.contains(tags))

        if overdue_only:
            query = query.where(Task.due_date < datetime.now(), Task.status != TaskStatus.COMPLETED)
            count_query = count_query.where(Task.due_date < datetime.now(), Task.status != TaskStatus.COMPLETED)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Task, sort_by):
            sort_column = getattr(Task, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Task.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, task: Task) -> Task:
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.db.delete(task)
        await self.db.flush()
