from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.document_intelligence.schemas import (
    DocumentPipelineRequest,
    DocumentPipelineResponse,
    DocumentPipelineStatusResponse,
)
from app.modules.document_intelligence.service import DocumentIntelligenceService, get_document_intelligence_service
from app.modules.users.models import User

router = APIRouter(prefix="/document-intelligence", tags=["Document Intelligence"])


@router.post("/process", response_model=DocumentPipelineResponse, status_code=status.HTTP_201_CREATED)
async def process_document_pipeline(
    data: DocumentPipelineRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_UPLOAD)),
):
    """Execute the full document intelligence pipeline on a document."""
    service = await get_document_intelligence_service(db)
    result = await service.process_document_full_pipeline(
        document_id=data.document_id,
        tenant_id=tenant_context.tenant_id,
        user_id=current_user.id,
        ocr_engine=data.ocr_engine,
        classification_model_id=data.classification_model_id,
        extraction_model_id=data.extraction_model_id,
        skip_review=data.skip_review,
    )
    return DocumentPipelineResponse(**result)


@router.get("/process/{document_id}/status", response_model=DocumentPipelineStatusResponse)
async def get_pipeline_status(
    document_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENTS_READ)),
):
    """Get the status of a document intelligence pipeline."""
    from app.modules.documents.models import Document
    from app.modules.ocr.models import OCRJob
    from app.modules.ai_processing.models import AIProcessingJob
    
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.tenant_id == tenant_context.tenant_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise NotFoundException(detail="Document not found")
    
    # Get OCR job status
    ocr_result = await db.execute(
        select(OCRJob).where(OCRJob.document_id == document_id, OCRJob.tenant_id == tenant_context.tenant_id)
        .order_by(OCRJob.created_at.desc())
    )
    ocr_job = ocr_result.scalars().first()
    
    # Get AI processing jobs
    ai_result = await db.execute(
        select(AIProcessingJob).where(AIProcessingJob.document_id == document_id, AIProcessingJob.tenant_id == tenant_context.tenant_id)
        .order_by(AIProcessingJob.created_at.desc())
    )
    ai_jobs = ai_result.scalars().all()
    
    return DocumentPipelineStatusResponse(
        document_id=document.id,
        document_status=document.status.value,
        ocr_status=ocr_job.status.value if ocr_job else "not_started",
        ocr_job_id=str(ocr_job.id) if ocr_job else None,
        ai_jobs=[
            {
                "job_id": str(job.id),
                "model_type": job.model.model_type.value if job.model else None,
                "status": job.status.value,
                "confidence_score": job.confidence_score,
            }
            for job in ai_jobs
        ],
        classification=document.classification,
        extracted_data=document.extracted_data,
        confidence_score=float(document.confidence_score) if document.confidence_score else None,
    )