from datetime import datetime
from uuid import UUID
import asyncio
import subprocess
import tempfile
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.storage.azure_blob import get_azure_blob_service
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
        self.settings = get_settings()

    async def create_job(self, data: OCRJobCreate, tenant_id: UUID, created_by: UUID) -> OCRJob:
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

    async def _download_document(self, document: Document) -> bytes:
        """Download document content from Azure Blob Storage."""
        azure_service = get_azure_blob_service()
        return await azure_service.download_blob(document.storage_key)

    async def _run_tesseract_ocr(self, file_content: bytes, language: str = "eng") -> tuple[str, float]:
        """Run tesseract OCR on file content."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name

        try:
            # Run tesseract with stdout output
            cmd = [
                "tesseract",
                tmp_path,
                "stdout",
                "-l", language,
                "--psm", "6",  # Assume single uniform block of text
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise ValidationException(f"Tesseract OCR failed: {stderr.decode()}")
            
            extracted_text = stdout.decode("utf-8", errors="replace").strip()
            
            # Tesseract doesn't provide confidence easily from stdout
            # Use a default high confidence for successful runs
            confidence = 0.9 if extracted_text else 0.0
            
            return extracted_text, confidence
            
        except FileNotFoundError:
            raise ValidationException("Tesseract OCR engine not installed. Please install tesseract-ocr.")
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

    async def _run_aws_textract_ocr(self, file_content: bytes) -> tuple[str, float]:
        """Run AWS Textract OCR (placeholder - requires AWS credentials)."""
        # Placeholder for AWS Textract integration
        # Would use boto3 textract client
        raise ValidationException("AWS Textract OCR not yet implemented. Configure AWS credentials and implement.")

    async def _run_google_vision_ocr(self, file_content: bytes) -> tuple[str, float]:
        """Run Google Vision OCR (placeholder - requires Google credentials)."""
        # Placeholder for Google Vision integration
        # Would use google-cloud-vision client
        raise ValidationException("Google Vision OCR not yet implemented. Configure Google credentials and implement.")

    async def _run_azure_form_recognizer_ocr(self, file_content: bytes) -> tuple[str, float]:
        """Run Azure Form Recognizer OCR (placeholder - requires Azure credentials)."""
        # Placeholder for Azure Form Recognizer integration
        # Would use azure-ai-formrecognizer client
        raise ValidationException("Azure Form Recognizer OCR not yet implemented. Configure Azure credentials and implement.")

    async def process_document(self, request: OCRProcessRequest, tenant_id: UUID, processed_by: UUID) -> OCRJob:
        doc_result = await self.db.execute(
            select(Document).where(Document.id == request.document_id, Document.tenant_id == tenant_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise NotFoundException(detail="Document not found")

        engine = request.engine or OCREngine.TESSERACT

        job = OCRJob(
            document_id=request.document_id,
            engine=engine,
            language=request.language,
            tenant_id=tenant_id,
            created_by=processed_by,
            status=OCRStatus.PENDING,
        )
        job = await self.job_repository.create(job)

        job.status = OCRStatus.PROCESSING
        job.started_at = datetime.now()
        await self.db.flush()

        try:
            # Download document from storage
            file_content = await self._download_document(document)
            
            # Run OCR based on engine
            extracted_text = ""
            confidence = 0.0
            
            if engine == OCREngine.TESSERACT:
                extracted_text, confidence = await self._run_tesseract_ocr(file_content, request.language)
            elif engine == OCREngine.AWS_TEXTRACT:
                extracted_text, confidence = await self._run_aws_textract_ocr(file_content)
            elif engine == OCREngine.GOOGLE_VISION:
                extracted_text, confidence = await self._run_google_vision_ocr(file_content)
            elif engine == OCREngine.AZURE_FORM_RECOGNIZER:
                extracted_text, confidence = await self._run_azure_form_recognizer_ocr(file_content)
            else:
                raise ValidationException(f"Unsupported OCR engine: {engine}")

            job.status = OCRStatus.COMPLETED
            job.completed_at = datetime.now()
            job.pages_processed = 1
            job.total_pages = 1
            job.extracted_text = extracted_text
            job.structured_data = {"pages": [{"page": 1, "text": extracted_text}]}
            job.confidence_score = confidence
            job.processing_time_ms = int((job.completed_at - job.started_at).total_seconds() * 1000) if job.started_at else 0

        except ValidationException as e:
            job.status = OCRStatus.FAILED
            job.completed_at = datetime.now()
            job.error_message = str(e)
            job.processing_time_ms = int((datetime.now() - job.started_at).total_seconds() * 1000) if job.started_at else 0
        except Exception as e:
            job.status = OCRStatus.FAILED
            job.completed_at = datetime.now()
            job.error_message = f"Unexpected error: {str(e)}"
            job.processing_time_ms = int((datetime.now() - job.started_at).total_seconds() * 1000) if job.started_at else 0

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