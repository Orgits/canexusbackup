from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.documents.models import Document
from app.modules.ocr.models import OCRJob, OCRTemplate, OCRStatus, OCREngine
from app.modules.ocr.repository import OCRJobRepository, OCRTemplateRepository
from app.modules.ocr.schemas import OCRJobCreate, OCRJobUpdate, OCRProcessRequest, OCRTemplateCreate, OCRTemplateUpdate
from app.modules.users.models import User


class OCRService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repository = OCRJobRepository(db)
        self.template_repository = OCRTemplateRepository(db)

    async def create_job(self, data: OCRJobCreate, tenant_id: UUID, created_by: UUID) -> OCRJob:
        # Validate document exists
        doc_result = await self.db.execute(
            select(Document).where(Document.id == data.document_id, Document.tenant_id == tenant_id)
        )
        if not doc_result.scalar_one_or_none():
            raise NotFoundException(detail="Document not found")

        job = OCRJob(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=OCRStatus.PENDING,
        )
        return await self.job_repository.create(job)

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> OCRJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="OCR job not found")
        return job

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        engine: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, engine, date_from, date_to)

    async def process_document(self, request: OCRProcessRequest, tenant_id: UUID, processed_by: UUID) -> OCRJob:
        # Validate document exists
        doc_result = await self.db.execute(
            select(Document).where(Document.id == request.document_id, Document.tenant_id == tenant_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise NotFoundException(detail="Document not found")

        # Determine engine
        engine = request.engine or OCREngine.TESSERACT

        # Create job
        job = OCRJob(
            document_id=request.document_id,
            engine=engine,
            language=request.language,
            tenant_id=tenant_id,
            created_by=processed_by,
            status=OCRStatus.PENDING,
        )
        job = await self.job_repository.create(job)

        # TODO: Actually run OCR processing
        # This would call the appropriate OCR engine
        # For now, mark as completed with placeholder text
        job.status = OCRStatus.PROCESSING
        job.started_at = datetime.now()
        await self.db.flush()

        # Simulate OCR processing
        job.status = OCRStatus.COMPLETED
        job.completed_at = datetime.now()
        job.pages_processed = 1
        job.total_pages = 1
        job.extracted_text = "Sample extracted text from document"
        job.structured_data = {"sample": "data"}
        job.confidence_score = 0.95
        job.processing_time_ms = 1000

        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def retry_job(self, job_id: UUID, tenant_id: UUID) -> OCRJob:
        job = await self.get_job(job_id, tenant_id)

        if job.status != OCRStatus.FAILED:
            raise ValueError("Can only retry failed jobs")

        if job.retry_count >= job.max_retries:
            raise ValueError("Maximum retry attempts exceeded")

        job.status = OCRStatus.PENDING
        job.retry_count += 1
        job.error_message = None
        job.started_at = None
        job.completed_at = None

        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> OCRJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="OCR job not found")
        return job

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        engine: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, engine, date_from, date_to)

    async def get_template(self, template_id: UUID, tenant_id: UUID) -> OCRTemplate:
        template = await self.template_repository.get_by_id(template_id, tenant_id)
        if not template:
            raise NotFoundException(detail="OCR template not found")
        return template

    async def list_templates(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engine: str | None = None,
        is_active: bool | None = None,
        is_default: bool | None = None,
    ) -> tuple[list, int]:
        return await self.template_repository.get_all(tenant_id, page, page_size, engine, is_active, is_default)

    async def create_template(self, data: OCRTemplateCreate, tenant_id: UUID, created_by: UUID) -> OCRTemplate:
        # Check for duplicate name
        existing = await self.template_repository.get_by_name(data.name, tenant_id)
        if existing:
            raise ValueError("Template with this name already exists")

        template = OCRTemplate(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.template_repository.create(template)

    async def get_template(self, template_id: UUID, tenant_id: UUID) -> OCRTemplate:
        return await self.template_repository.get_by_id(template_id, tenant_id)

    async def update_template(self, template_id: UUID, tenant_id: UUID, data: OCRTemplateUpdate, updated_by: UUID) -> OCRTemplate:
        template = await self.get_template(template_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)

        return await self.template_repository.update(template)

    async def delete_template(self, template_id: UUID, tenant_id: UUID) -> None:
        template = await self.get_template(template_id, tenant_id)
        await self.template_repository.delete(template)

    async def set_default_template(self, template_id: UUID, tenant_id: UUID) -> OCRTemplate:
        template = await self.get_template(template_id, tenant_id)

        # Unset current default
        result = await self.db.execute(
            select(OCRTemplate).where(
                OCRTemplate.engine == template.engine,
                OCRTemplate.tenant_id == tenant_id,
                OCRTemplate.is_default == True,
            )
        )
        current_default = result.scalars().first()
        if current_default:
            current_default.is_default = False

        template.is_default = True
        await self.db.flush()
        await self.db.refresh(template)

        return template