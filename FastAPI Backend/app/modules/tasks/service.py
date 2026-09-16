from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.clients.models import Client
from app.modules.communications.models import Communication
from app.modules.matters.models import Matter
from app.modules.tasks.models import Task, TaskPriority, TaskStatus
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import TaskAction, TaskCreate, TaskUpdate
from app.modules.users.models import Team, User


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = TaskRepository(db)

    async def create(self, data: TaskCreate, tenant_id: UUID, created_by: UUID) -> Task:
        if data.task_number:
            existing = await self.repository.get_by_number(data.task_number, tenant_id)
            if existing:
                raise ConflictException(detail="Task with this number already exists")

        if data.client_id:
            client_result = await self.db.execute(
                select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        if data.matter_id:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == data.matter_id, Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        if data.parent_task_id:
            parent_result = await self.db.execute(
                select(Task).where(Task.id == data.parent_task_id, Task.tenant_id == tenant_id)
            )
            if not parent_result.scalar_one_or_none():
                raise NotFoundException(detail="Parent task not found")

        if data.assignee_id:
            user_result = await self.db.execute(
                select(User).where(User.id == data.assignee_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="Assignee not found")

        if data.team_id:
            team_result = await self.db.execute(
                select(Team).where(Team.id == data.team_id, Team.tenant_id == tenant_id)
            )
            if not team_result.scalar_one_or_none():
                raise NotFoundException(detail="Team not found")

        if data.source_communication_id:
            comm_result = await self.db.execute(
                select(Communication).where(Communication.id == data.source_communication_id, Communication.tenant_id == tenant_id)
            )
            if not comm_result.scalar_one_or_none():
                raise NotFoundException(detail="Source communication not found")

        for dep_id in data.dependencies:
            dep_result = await self.db.execute(
                select(Task).where(Task.id == dep_id, Task.tenant_id == tenant_id)
            )
            if not dep_result.scalar_one_or_none():
                raise NotFoundException(detail=f"Dependency task {dep_id} not found")

        task = Task(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            reporter_id=created_by,
            status=TaskStatus.TODO,
        )
        return await self.repository.create(task)

    async def get_by_id(self, task_id: UUID, tenant_id: UUID) -> Task:
        task = await self.repository.get_by_id(task_id, tenant_id)
        if not task:
            raise NotFoundException(detail="Task not found")
        return task

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
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, matter_id,
            status, priority, assignee_id, team_id, due_date_from, due_date_to,
            tags, overdue_only, sort_by, sort_order
        )

    async def update(self, task_id: UUID, tenant_id: UUID, data: TaskUpdate, updated_by: UUID) -> Task:
        task = await self.get_by_id(task_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("task_number"):
            existing = await self.repository.get_by_number(update_data["task_number"], tenant_id)
            if existing and existing.id != task_id:
                raise ConflictException(detail="Task with this number already exists")

        if update_data.get("assignee_id"):
            user_result = await self.db.execute(
                select(User).where(User.id == update_data["assignee_id"], User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="Assignee not found")

        if update_data.get("team_id"):
            team_result = await self.db.execute(
                select(Team).where(Team.id == update_data["team_id"], Team.tenant_id == tenant_id)
            )
            if not team_result.scalar_one_or_none():
                raise NotFoundException(detail="Team not found")

        if update_data.get("parent_task_id"):
            parent_result = await self.db.execute(
                select(Task).where(Task.id == update_data["parent_task_id"], Task.tenant_id == tenant_id)
            )
            if not parent_result.scalar_one_or_none():
                raise NotFoundException(detail="Parent task not found")

        if "dependencies" in update_data:
            for dep_id in update_data["dependencies"]:
                dep_result = await self.db.execute(
                    select(Task).where(Task.id == dep_id, Task.tenant_id == tenant_id)
                )
                if not dep_result.scalar_one_or_none():
                    raise NotFoundException(detail=f"Dependency task {dep_id} not found")

        for field, value in update_data.items():
            setattr(task, field, value)
        task.updated_by = updated_by

        if task.status == TaskStatus.COMPLETED and not task.completed_date:
            task.completed_date = datetime.now(UTC)
            task.progress_percentage = 100

        return await self.repository.update(task)

    async def perform_action(self, task_id: UUID, tenant_id: UUID, action: TaskAction, performed_by: UUID) -> Task:
        task = await self.get_by_id(task_id, tenant_id)

        if action.action == "complete":
            task.status = TaskStatus.COMPLETED
            task.completed_date = datetime.now(UTC)
            task.progress_percentage = 100
        elif action.action == "reassign":
            if not action.assignee_id:
                raise ConflictException(detail="Assignee required for reassignment")
            user_result = await self.db.execute(
                select(User).where(User.id == action.assignee_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="Assignee not found")
            task.assignee_id = action.assignee_id
        elif action.action == "change_status":
            if not action.status:
                raise ConflictException(detail="Status required for status change")
            task.status = action.status
            if action.status == TaskStatus.COMPLETED:
                task.completed_date = datetime.now(UTC)
                task.progress_percentage = 100
        elif action.action == "submit_for_review":
            task.status = TaskStatus.IN_REVIEW
        elif action.action == "start":
            task.status = TaskStatus.IN_PROGRESS
            if not task.start_date:
                task.start_date = datetime.now(UTC)
        elif action.action == "put_on_hold":
            task.status = TaskStatus.ON_HOLD
        elif action.action == "cancel":
            task.status = TaskStatus.CANCELLED
        else:
            raise ConflictException(detail=f"Unknown action: {action.action}")

        task.updated_by = performed_by
        return await self.repository.update(task)

    async def delete(self, task_id: UUID, tenant_id: UUID) -> None:
        task = await self.get_by_id(task_id, tenant_id)
        await self.repository.delete(task)
