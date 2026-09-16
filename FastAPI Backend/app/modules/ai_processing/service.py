from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.ai_processing.models import AIModel, AIProcessingJob, AIProcessingStatus, AIConfidenceThreshold, AIReviewTask, AIModelType, AIModelProvider
from app.modules.ai_processing.repository import AIModelRepository, AIProcessingJobRepository, AIConfidenceThresholdRepository, AIReviewTaskRepository
from app.modules.ai_processing.schemas import (
    AIModelCreate,
    AIModelUpdate,
    AIProcessingJobCreate,
    AIProcessingJobUpdate,
    AIProcessRequest,
    AIConfidenceThresholdCreate,
    AIConfidenceThresholdUpdate,
    AIReviewTaskCreate,
    AIReviewTaskUpdate,
)
from app.modules.documents.models import Document
from app.modules.users.models import User


class AIModelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AIModelRepository(db)

    async def create(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIModel:
        model = AIModel(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def get_by_id(self, model_id: UUID, tenant_id: UUID) -> AIModel:
        model = await self.repository.get_by_id(model_id, tenant_id)
        if not model:
            raise NotFoundException(detail="AI model not found")
        return model

    async def get_default(self, model_type: str, tenant_id: UUID) -> AIModel:
        model = await self.repository.get_default(model_type, tenant_id)
        if not model:
            raise NotFoundException(detail=f"No default model found for type {model_type}")
        return model

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        model_type: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list, int]:
        return await self.repository.get_all(tenant_id, page, page_size, model_type, provider, is_active)

    async def update(self, model_id: UUID, tenant_id: UUID, data: dict, updated_by: UUID) -> AIModel:
        model = await self.get_by_id(model_id, tenant_id)

        for field, value in data.items():
            if hasattr(model, field):
                setattr(model, field, value)

        model.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def delete(self, model_id: UUID, tenant_id: UUID) -> None:
        model = await self.get_by_id(model_id, tenant_id)
        await self.db.delete(model)
        await self.db.flush()

    async def set_default(self, model_id: UUID, tenant_id: UUID) -> AIModel:
        model = await self.get_by_id(model_id, tenant_id)

        # Unset current default
        result = await self.db.execute(
            select(AIModel).where(
                AIModel.model_type == model.model_type,
                AIModel.tenant_id == tenant_id,
                AIModel.is_default == True,
            )
        )
        current_default = result.scalars().first()
        if current_default:
            current_default.is_default = False

        model.is_default = True
        await self.db.flush()
        await self.db.refresh(model)
        return model


class AIProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repository = AIProcessingJobRepository(db)
        self.model_repository = AIModelRepository(db)

    async def create_job(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIProcessingJob:
        # Validate document exists
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == data["document_id"], Document.tenant_id == tenant_id)
        )
        if not doc_result.scalar_one_or_none():
            raise NotFoundException(detail="Document not found")

        # Validate model exists
        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == data["model_id"], AIModel.tenant_id == tenant_id)
        )
        if not model_result.scalar_one_or_none():
            raise NotFoundException(detail="AI model not found")

        job = AIProcessingJob(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
            status=AIProcessingStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="AI processing job not found")
        return job

    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list:
        return await self.job_repository.get_by_document(document_id, tenant_id)

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        model_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, model_id, date_from, date_to)

    async def process_document(self, request: dict, tenant_id: UUID, processed_by: UUID) -> AIProcessingJob:
        # Validate document
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == request["document_id"], Document.tenant_id == tenant_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise NotFoundException(detail="Document not found")

        # Get model
        model_id = request.get("model_id")
        if not model_id:
            raise ValueError("Model ID is required")

        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == tenant_id)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise NotFoundException(detail="AI model not found")

        # Create job
        job = AIProcessingJob(
            document_id=request["document_id"],
            model_id=model_id,
            prompt=request.get("prompt"),
            input_data=request.get("input_data", {}),
            tenant_id=tenant_id,
            created_by=processed_by,
            status=AIProcessingStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()

        # TODO: Actually run AI processing
        # This would call the appropriate AI model (OpenAI, Anthropic, etc.)
        # For now, mark as completed with placeholder output
        job.status = AIProcessingStatus.PROCESSING
        job.started_at = datetime.now()
        await self.db.flush()

        # Simulate AI processing
        job.status = AIProcessingStatus.COMPLETED
        job.completed_at = datetime.now()
        job.output_data = {"result": "Sample AI processing result"}
        job.confidence_score = 0.92
        job.processing_time_ms = 1500
        job.tokens_used = 150
        job.cost = 0.002

        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="AI processing job not found")
        return job

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        model_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, model_id, date_from, date_to)

    async def retry_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="Job not found")

        if job.status not in [AIProcessingStatus.FAILED, AIProcessingStatus.PENDING]:
            raise ValueError("Can only retry failed or pending jobs")

        job.status = AIProcessingStatus.PENDING
        job.retry_count += 1
        job.error_message = None
        await self.db.flush()
        await self.db.refresh(job)
        return job


class AIConfidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AIConfidenceThresholdRepository(db)

    async def create_threshold(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIConfidenceThreshold:
        threshold = AIConfidenceThreshold(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.db.add(threshold)
        await self.db.flush()
        await self.db.refresh(threshold)
        return threshold

    async def get_by_type(self, model_type: str, tenant_id: UUID) -> AIConfidenceThreshold | None:
        return await self.repository.get_by_type(model_type, tenant_id)

    async def get_all(self, tenant_id: UUID) -> list:
        return await self.repository.get_all(tenant_id)

    async def update(self, threshold_id: UUID, tenant_id: UUID, data: dict, updated_by: UUID) -> AIConfidenceThreshold:
        threshold = await self.repository.get_by_type(threshold_id, tenant_id)
        if not threshold:
            raise NotFoundException(detail="Threshold not found")

        for field, value in data.items():
            if hasattr(threshold, field):
                setattr(threshold, field, value)

        threshold.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(threshold)
        return threshold

    async def evaluate_confidence(self, model_type: str, tenant_id: UUID, confidence: float) -> dict:
        threshold = await self.get_by_type(model_type, tenant_id)
        if not threshold:
            return {"action": "review", "reason": "No threshold configured"}

        if confidence >= threshold.auto_approve_threshold:
            return {"action": threshold.auto_approve_action, "threshold": threshold.auto_approve_threshold}
        elif confidence <= threshold.auto_reject_threshold:
            return {"action": threshold.auto_reject_action, "threshold": threshold.auto_reject_threshold}
        else:
            return {"action": threshold.requires_review_action, "threshold": threshold.requires_review_threshold}