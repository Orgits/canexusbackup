"""Document Intelligence Pipeline Service.

Orchestrates the complete document processing pipeline:
Upload → Verification → OCR → Classification → Extraction → Confidence → Review → Storage
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.storage.azure_blob import get_azure_blob_service
from app.modules.ai_processing.models import AIModel, AIProcessingJob, AIProcessingStatus, AIModelType
from app.modules.ai_processing.service import AIProcessingService, AIConfidenceService
from app.modules.documents.models import Document, DocumentStatus
from app.modules.ocr.models import OCRJob, OCRStatus, OCREngine
from app.modules.ocr.service import OCRService
from app.modules.mongodb.manager import get_mongodb, RawPayloadService, DocumentRawService


class DocumentIntelligenceService:
    """Service orchestrating the complete document intelligence pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.ocr_service = OCRService(db)
        self.ai_service = AIProcessingService(db)
        self.confidence_service = AIConfidenceService(db)

    async def process_document_full_pipeline(
        self,
        document_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        ocr_engine: str = "tesseract",
        classification_model_id: UUID | None = None,
        extraction_model_id: UUID | None = None,
        skip_review: bool = False,
    ) -> dict:
        """Execute the full document intelligence pipeline.
        
        Pipeline stages:
        1. Document Verification (already done at upload)
        2. OCR Processing
        3. Document Classification
        4. Structured Extraction
        5. Confidence Scoring
        6. Manual Review (if confidence below threshold)
        7. Store results in PostgreSQL, MongoDB, OpenSearch
        """
        # Get document
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise NotFoundException(detail="Document not found")

        pipeline_result = {
            "document_id": str(document_id),
            "stages": {},
            "final_status": "processing",
            "review_required": False,
        }

        try:
            # Stage 1: OCR Processing
            pipeline_result["stages"]["ocr"] = await self._run_ocr_stage(
                document, tenant_id, user_id, ocr_engine
            )
            
            # Refresh document to get OCR text
            await self.db.refresh(document)
            
            # Stage 2: Classification
            if classification_model_id:
                pipeline_result["stages"]["classification"] = await self._run_classification_stage(
                    document, tenant_id, user_id, classification_model_id
                )
            
            # Stage 3: Extraction
            if extraction_model_id:
                pipeline_result["stages"]["extraction"] = await self._run_extraction_stage(
                    document, tenant_id, user_id, extraction_model_id
                )
            
            # Stage 4: Confidence Evaluation
            pipeline_result["stages"]["confidence"] = await self._run_confidence_stage(
                document, tenant_id
            )
            
            # Stage 5: Review Decision
            review_decision = await self._evaluate_review_need(document, tenant_id)
            pipeline_result["stages"]["review_decision"] = review_decision
            pipeline_result["review_required"] = review_decision.get("requires_review", False)
            
            # Stage 6: Store Results
            await self._store_results(document, tenant_id, user_id)
            pipeline_result["stages"]["storage"] = {"status": "completed"}
            
            # Update document status
            document.status = DocumentStatus.PROCESSED
            document.classification = getattr(document, 'classification', None)
            await self.db.flush()
            
            pipeline_result["final_status"] = "completed"
            
        except Exception as e:
            pipeline_result["final_status"] = "failed"
            pipeline_result["error"] = str(e)
            document.status = DocumentStatus.FAILED
            await self.db.flush()
            raise
        
        await self.db.commit()
        return pipeline_result

    async def _run_ocr_stage(
        self, document: "Document", tenant_id: UUID, user_id: UUID, ocr_engine: str
    ) -> dict:
        """Run OCR on document."""
        from app.modules.ocr.schemas import OCRProcessRequest
        
        ocr_request = OCRProcessRequest(
            document_id=document.id,
            engine=ocr_engine,
            language="eng",
        )
        
        job = await self.ocr_service.process_document(ocr_request, tenant_id, user_id)
        
        # Update document with OCR results
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == document.id)
        )
        doc = doc_result.scalar_one()
        doc.ocr_text = job.extracted_text
        doc.confidence_score = job.confidence_score
        await self.db.flush()
        
        return {
            "job_id": str(job.id),
            "status": job.status.value,
            "extracted_text_length": len(job.extracted_text or ""),
            "confidence_score": job.confidence_score,
            "processing_time_ms": job.processing_time_ms,
        }

    async def _run_classification_stage(
        self, document: "Document", tenant_id: UUID, user_id: UUID, model_id: UUID
    ) -> dict:
        """Run document classification using AI model."""
        # Get classification model
        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == tenant_id)
        )
        model = model_result.scalar_one_or_none()
        if not model or model.model_type != AIModelType.CLASSIFICATION:
            raise ValidationException("Invalid classification model")
        
        # Process with AI
        job = await self.ai_service.process_document(
            {
                "document_id": document.id,
                "model_id": model_id,
                "prompt": None,
                "input_data": {},
            },
            tenant_id,
            user_id,
        )
        
        # Update document with classification
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == document.id)
        )
        doc = doc_result.scalar_one()
        if job.output_data and isinstance(job.output_data, dict):
            doc.classification = job.output_data.get("category")
        
        await self.db.flush()
        
        return {
            "job_id": str(job.id),
            "status": job.status.value,
            "classification": doc.classification,
            "confidence_score": job.confidence_score,
        }

    async def _run_extraction_stage(
        self, document: "Document", tenant_id: UUID, user_id: UUID, model_id: UUID
    ) -> dict:
        """Run structured extraction using AI model."""
        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == tenant_id)
        )
        model = model_result.scalar_one_or_none()
        if not model or model.model_type != AIModelType.EXTRACTION:
            raise ValidationException("Invalid extraction model")
        
        job = await self.ai_service.process_document(
            {
                "document_id": document.id,
                "model_id": model_id,
                "prompt": None,
                "input_data": {"fields": []},
            },
            tenant_id,
            user_id,
        )
        
        # Update document with extracted data
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == document.id)
        )
        doc = doc_result.scalar_one()
        if job.output_data and isinstance(job.output_data, dict):
            doc.extracted_data = job.output_data
        
        await self.db.flush()
        
        return {
            "job_id": str(job.id),
            "status": job.status.value,
            "extracted_fields": list(job.output_data.keys()) if job.output_data else [],
            "confidence_score": job.confidence_score,
        }

    async def _run_confidence_stage(self, document: "Document", tenant_id: UUID) -> dict:
        """Evaluate confidence scores and determine review requirements."""
        # Get the latest AI processing job for this document
        from app.modules.ai_processing.models import AIProcessingJob
        job_result = await self.db.execute(
            select(AIProcessingJob)
            .where(
                AIProcessingJob.document_id == document.id,
                AIProcessingJob.tenant_id == tenant_id,
                AIProcessingJob.status == "completed",
            )
            .order_by(AIProcessingJob.completed_at.desc())
        )
        job = job_result.scalars().first()
        
        if not job:
            return {"status": "no_ai_job", "confidence": None}
        
        confidence = job.confidence_score or 0.0
        model_type = job.model.model_type.value if job.model else "unknown"
        
        evaluation = await self.confidence_service.evaluate_confidence(
            model_type, tenant_id, confidence
        )
        
        return {
            "confidence": confidence,
            "model_type": model_type,
            "evaluation": evaluation,
        }

    async def _evaluate_review_need(self, document: "Document", tenant_id: UUID) -> dict:
        """Determine if manual review is required based on confidence thresholds."""
        # Get the latest AI processing job
        from app.modules.ai_processing.models import AIProcessingJob
        job_result = await self.db.execute(
            select(AIProcessingJob)
            .where(
                AIProcessingJob.document_id == document.id,
                AIProcessingJob.tenant_id == tenant_id,
                AIProcessingJob.status == "completed",
            )
            .order_by(AIProcessingJob.completed_at.desc())
        )
        job = job_result.scalars().first()
        
        if not job:
            return {"requires_review": True, "reason": "No AI processing completed"}
        
        confidence = job.confidence_score or 0.0
        model_type = job.model.model_type.value if job.model else "unknown"
        
        evaluation = await self.confidence_service.evaluate_confidence(
            model_type, tenant_id, confidence
        )
        
        requires_review = evaluation.get("action") == "review"
        
        return {
            "requires_review": requires_review,
            "action": evaluation.get("action"),
            "confidence": confidence,
            "thresholds": {
                "auto_approve": None,
                "auto_reject": None,
                "review": None,
            },
        }

    async def _store_results(
        self, document: "Document", tenant_id: UUID, user_id: UUID
    ) -> None:
        """Store document intelligence results in MongoDB and OpenSearch."""
        # Store in MongoDB (raw payloads)
        try:
            mongodb = await get_mongodb()
            
            # Store document raw content
            doc_raw_service = DocumentRawService(mongodb.db)
            await doc_raw_service.store_document_raw(
                tenant_id=tenant_id,
                document_id=document.id,
                content=document.ocr_text or "",
                extracted_data=document.extracted_data,
                ocr_result={"text": document.ocr_text},
                metadata={
                    "classification": document.classification,
                    "confidence_score": float(document.confidence_score) if document.confidence_score else None,
                    "processed_at": datetime.utcnow().isoformat(),
                },
            )
            
            # Store AI raw payloads
            from app.modules.ai_processing.models import AIProcessingJob
            job_result = await self.db.execute(
                select(AIProcessingJob)
                .where(
                    AIProcessingJob.document_id == document.id,
                    AIProcessingJob.tenant_id == tenant_id,
                )
                .order_by(AIProcessingJob.completed_at.desc())
            )
            jobs = job_result.scalars().all()
            
            ai_raw_service = RawPayloadService(mongodb.db)
            for job in jobs:
                await ai_raw_service.store_raw_payload(
                    tenant_id=tenant_id,
                    source="ai_processing",
                    payload={
                        "input_data": job.input_data,
                        "output_data": job.output_data,
                        "model_type": job.model.model_type.value if job.model else None,
                        "confidence_score": job.confidence_score,
                        "processing_time_ms": job.processing_time_ms,
                        "tokens_used": job.tokens_used,
                        "cost": job.cost,
                    },
                    document_id=document.id,
                    metadata={
                        "job_id": str(job.id),
                        "model_id": str(job.model_id) if job.model_id else None,
                    },
                )
        except Exception as e:
            # Log but don't fail the pipeline for MongoDB issues
            import logging
            logging.getLogger(__name__).warning(f"MongoDB storage failed: {e}")

        # Index in OpenSearch
        try:
            from app.modules.opensearch.manager import get_opensearch
            opensearch = await get_opensearch()
            os_service = opensearch.client
            
            # Index document
            await os_service.index_document(
                tenant_id=str(tenant_id),
                document_id=str(document.id),
                title=document.title or document.filename,
                content=document.description or "",
                extracted_text=document.ocr_text,
                structured_data=document.extracted_data,
                metadata=document.extra_metadata,
                tags=document.tags,
                category=document.category.value if document.category else None,
                status=document.status.value if document.status else None,
                created_at=document.created_at,
                updated_at=document.updated_at,
                created_by=str(document.uploaded_by) if document.uploaded_by else None,
                client_id=str(document.client_id) if document.client_id else None,
                matter_id=str(document.matter_id) if document.matter_id else None,
            )
        except Exception as e:
            # Log but don't fail for OpenSearch issues
            import logging
            logging.getLogger(__name__).warning(f"OpenSearch indexing failed: {e}")


async def get_document_intelligence_service(db: AsyncSession) -> DocumentIntelligenceService:
    return DocumentIntelligenceService(db)