from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ai_processing.models import AIModel, AIProcessingJob, AIProcessingStatus, AIConfidenceThreshold, AIReviewTask


class AIModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, model: AIModel) -> AIModel:
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def get_by_id(self, model_id: UUID, tenant_id: UUID) -> AIModel | None:
        result = await self.db.execute(
            select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_default(self, model_type: str, tenant_id: UUID) -> AIModel | None:
        result = await self.db.execute(
            select(AIModel).where(
                AIModel.model_type == model_type,
                AIModel.tenant_id == tenant_id,
                AIModel.is_default == True,
                AIModel.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        model_type: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[AIModel], int]:
        query = select(AIModel).where(AIModel.tenant_id == tenant_id)
        count_query = select(func.count(AIModel.id)).where(AIModel.tenant_id == tenant_id)

        if model_type:
            query = query.where(AIModel.model_type == model_type)
            count_query = count_query.where(AIModel.model_type == model_type)

        if provider:
            query = query.where(AIModel.provider == provider)
            count_query = count_query.where(AIModel.provider == provider)

        if is_active is not None:
            query = query.where(AIModel.is_active == is_active)
            count_query = count_query.where(AIModel.is_active == is_active)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(AIModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, model: AIModel) -> AIModel:
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def delete(self, model: AIModel) -> None:
        await self.db.delete(model)
        await self.db.flush()


class AIProcessingJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, job: AIProcessingJob) -> AIProcessingJob:
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob | None:
        result = await self.db.execute(
            select(AIProcessingJob)
            .options(
                selectinload(AIProcessingJob.model),
                selectinload(AIProcessingJob.document),
            )
            .where(AIProcessingJob.id == job_id, AIProcessingJob.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list[AIProcessingJob]:
        result = await self.db.execute(
            select(AIProcessingJob).where(
                AIProcessingJob.document_id == document_id,
                AIProcessingJob.tenant_id == tenant_id,
            ).order_by(AIProcessingJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        model_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[AIProcessingJob], int]:
        query = select(AIProcessingJob).where(AIProcessingJob.tenant_id == tenant_id)
        count_query = select(func.count(AIProcessingJob.id)).where(AIProcessingJob.tenant_id == tenant_id)

        if status:
            query = query.where(AIProcessingJob.status == status)
            count_query = count_query.where(AIProcessingJob.status == status)

        if model_id:
            query = query.where(AIProcessingJob.model_id == model_id)
            count_query = count_query.where(AIProcessingJob.model_id == model_id)

        if date_from:
            query = query.where(AIProcessingJob.created_at >= date_from)
            count_query = count_query.where(AIProcessingJob.created_at >= date_from)

        if date_to:
            query = query.where(AIProcessingJob.created_at <= date_to)
            count_query = count_query.where(AIProcessingJob.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(AIProcessingJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, job: AIProcessingJob) -> AIProcessingJob:
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def delete(self, job: AIProcessingJob) -> None:
        await self.db.delete(job)
        await self.db.flush()


class AIConfidenceThresholdRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, threshold: AIConfidenceThreshold) -> AIConfidenceThreshold:
        self.db.add(threshold)
        await self.db.flush()
        await self.db.refresh(threshold)
        return threshold

    async def get_by_type(self, model_type: str, tenant_id: UUID) -> AIConfidenceThreshold | None:
        result = await self.db.execute(
            select(AIConfidenceThreshold).where(
                AIConfidenceThreshold.model_type == model_type,
                AIConfidenceThreshold.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, tenant_id: UUID) -> list[AIConfidenceThreshold]:
        result = await self.db.execute(
            select(AIConfidenceThreshold).where(AIConfidenceThreshold.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def update(self, threshold: AIConfidenceThreshold) -> AIConfidenceThreshold:
        await self.db.flush()
        await self.db.refresh(threshold)
        return threshold

    async def delete(self, threshold: AIConfidenceThreshold) -> None:
        await self.db.delete(threshold)
        await self.db.flush()


class AIReviewTaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: AIReviewTask) -> AIReviewTask:
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID, tenant_id: UUID) -> AIReviewTask | None:
        result = await self.db.execute(
            select(AIReviewTask)
            .options(selectinload(AIReviewTask.assignee))
            .where(AIReviewTask.id == task_id, AIReviewTask.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_job(self, job_id: UUID, tenant_id: UUID) -> AIReviewTask | None:
        result = await self.db.execute(
            select(AIReviewTask).where(AIReviewTask.job_id == job_id, AIReviewTask.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        assignee_id: UUID | None = None,
    ) -> tuple[list[AIReviewTask], int]:
        query = select(AIReviewTask).options(selectinload(AIReviewTask.assignee)).where(AIReviewTask.tenant_id == tenant_id)
        count_query = select(func.count(AIReviewTask.id)).where(AIReviewTask.tenant_id == tenant_id)

        if status:
            query = query.where(AIReviewTask.status == status)
            count_query = count_query.where(AIReviewTask.status == status)

        if assignee_id:
            query = query.where(AIReviewTask.assignee_id == assignee_id)
            count_query = count_query.where(AIReviewTask.assignee_id == assignee_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(AIReviewTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, task: AIReviewTask) -> AIReviewTask:
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete(self, task: AIReviewTask) -> None:
        await self.db.delete(task)
        await self.db.flush()