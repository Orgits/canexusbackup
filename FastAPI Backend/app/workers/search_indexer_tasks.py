import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.modules.opensearch.manager import get_opensearch, OpenSearchService
from app.modules.documents.models import Document
from app.modules.communications.models import Communication
from app.modules.ai_processing.models import AIProcessingJob

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, autoretry_for=(Exception,))
def index_document_task(self, tenant_id: str, document_id: str):
    """Index a single document in OpenSearch."""
    return asyncio.run(_index_document_async(tenant_id, document_id))


async def _index_document_async(tenant_id: str, document_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        
        try:
            result = await db.execute(
                select(Document).where(
                    Document.id == UUID(document_id),
                    Document.tenant_id == UUID(tenant_id),
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                logger.warning("Document not found for indexing", document_id=document_id, tenant_id=tenant_id)
                return
            
            manager = await get_opensearch()
            service = OpenSearchService(manager.client)
            
            await service.index_document(
                tenant_id=tenant_id,
                document_id=str(document.id),
                title=document.filename,
                content=document.ocr_text or "",
                extracted_text=document.ocr_text,
                structured_data=document.extracted_data or {},
                metadata=document.metadata or {},
                tags=document.tags or [],
                category=document.category.value if document.category else None,
                status=document.status.value if document.status else None,
                created_at=document.created_at,
                updated_at=document.updated_at,
                created_by=str(document.created_by_id) if document.created_by_id else None,
                client_id=str(document.client_id) if document.client_id else None,
                matter_id=str(document.matter_id) if document.matter_id else None,
            )
            
            logger.info("Document indexed", document_id=document_id, tenant_id=tenant_id)
            
        except Exception as e:
            logger.error("Document indexing failed", document_id=document_id, tenant_id=tenant_id, error=str(e))
            raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, autoretry_for=(Exception,))
def index_communication_task(self, tenant_id: str, communication_id: str):
    """Index a single communication in OpenSearch."""
    return asyncio.run(_index_communication_async(tenant_id, communication_id))


async def _index_communication_async(tenant_id: str, communication_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        
        try:
            result = await db.execute(
                select(Communication).where(
                    Communication.id == UUID(communication_id),
                    Communication.tenant_id == UUID(tenant_id),
                )
            )
            communication = result.scalar_one_or_none()
            
            if not communication:
                logger.warning("Communication not found for indexing", communication_id=communication_id, tenant_id=tenant_id)
                return
            
            manager = await get_opensearch()
            service = OpenSearchService(manager.client)
            
            await service.index_communication(
                tenant_id=tenant_id,
                communication_id=str(communication.id),
                channel=communication.channel.value if communication.channel else None,
                direction=communication.direction.value if communication.direction else None,
                subject=communication.subject,
                body=communication.body or "",
                from_address=communication.from_address,
                to_addresses=communication.to_addresses or [],
                thread_id=str(communication.thread_id) if communication.thread_id else None,
                conversation_id=str(communication.conversation_id) if communication.conversation_id else None,
                status=communication.status.value if communication.status else None,
                sent_at=communication.sent_at,
                delivered_at=communication.delivered_at,
                read_at=communication.read_at,
                client_id=str(communication.client_id) if communication.client_id else None,
                matter_id=str(communication.matter_id) if communication.matter_id else None,
            )
            
            logger.info("Communication indexed", communication_id=communication_id, tenant_id=tenant_id)
            
        except Exception as e:
            logger.error("Communication indexing failed", communication_id=communication_id, tenant_id=tenant_id, error=str(e))
            raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, autoretry_for=(Exception,))
def index_ai_job_task(self, tenant_id: str, job_id: str):
    """Index a single AI processing job in OpenSearch."""
    return asyncio.run(_index_ai_job_async(tenant_id, job_id))


async def _index_ai_job_async(tenant_id: str, job_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        
        try:
            result = await db.execute(
                select(AIProcessingJob).where(
                    AIProcessingJob.id == UUID(job_id),
                    AIProcessingJob.tenant_id == UUID(tenant_id),
                )
            )
            job = result.scalar_one_or_none()
            
            if not job:
                logger.warning("AI job not found for indexing", job_id=job_id, tenant_id=tenant_id)
                return
            
            manager = await get_opensearch()
            service = OpenSearchService(manager.client)
            
            await service.index_ai_job(
                tenant_id=tenant_id,
                job_id=str(job.id),
                document_id=str(job.document_id) if job.document_id else None,
                model_id=str(job.model_id) if job.model_id else None,
                model_type=job.model.model_type.value if job.model else None,
                input_data=job.input_data,
                output_data=job.output_data,
                confidence_score=job.confidence_score,
                processing_time_ms=job.processing_time_ms,
                tokens_used=job.tokens_used,
                cost=job.cost,
                status=job.status.value if job.status else None,
                error_message=job.error_message,
            )
            
            logger.info("AI job indexed", job_id=job_id, tenant_id=tenant_id)
            
        except Exception as e:
            logger.error("AI job indexing failed", job_id=job_id, tenant_id=tenant_id, error=str(e))
            raise


@shared_task
def reindex_entity_type_task(tenant_id: str, entity_type: str):
    """Reindex all entities of a specific type for a tenant."""
    return asyncio.run(_reindex_entity_type_async(tenant_id, entity_type))


async def _reindex_entity_type_async(tenant_id: str, entity_type: str):
    async with AsyncSessionLocal() as db:
        await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        
        try:
            manager = await get_opensearch()
            service = OpenSearchService(manager.client)
            
            if entity_type == "documents":
                result = await db.execute(
                    select(Document).where(Document.tenant_id == UUID(tenant_id))
                )
                documents = result.scalars().all()
                
                docs_to_index = []
                for doc in documents:
                    docs_to_index.append({
                        "document_id": str(doc.id),
                        "title": doc.filename,
                        "content": doc.ocr_text or "",
                        "extracted_text": doc.ocr_text,
                        "structured_data": doc.extracted_data or {},
                        "metadata": doc.metadata or {},
                        "tags": doc.tags or [],
                        "category": doc.category.value if doc.category else None,
                        "status": doc.status.value if doc.status else None,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                        "created_by": str(doc.created_by_id) if doc.created_by_id else None,
                        "client_id": str(doc.client_id) if doc.client_id else None,
                        "matter_id": str(doc.matter_id) if doc.matter_id else None,
                    })
                
                if docs_to_index:
                    await service.bulk_index_documents(tenant_id, docs_to_index)
                
                logger.info("Documents reindexed", tenant_id=tenant_id, count=len(documents))
            
            elif entity_type == "communications":
                result = await db.execute(
                    select(Communication).where(Communication.tenant_id == UUID(tenant_id))
                )
                communications = result.scalars().all()
                
                logger.info("Communications reindex queued", tenant_id=tenant_id, count=len(communications))
            
            elif entity_type == "ai-jobs":
                result = await db.execute(
                    select(AIProcessingJob).where(AIProcessingJob.tenant_id == UUID(tenant_id))
                )
                jobs = result.scalars().all()
                
                logger.info("AI jobs reindex queued", tenant_id=tenant_id, count=len(jobs))
            
        except Exception as e:
            logger.error("Reindex failed", tenant_id=tenant_id, entity_type=entity_type, error=str(e))
            raise


@shared_task
def process_search_index_queue():
    """Process the search index queue from outbox events."""
    return asyncio.run(_process_search_index_queue_async())


async def _process_search_index_queue_async():
    async with AsyncSessionLocal() as db:
        from app.modules.outbox.repository import OutboxRepository
        from app.modules.outbox.models import OutboxEventType, OutboxStatus
        
        from app.modules.firms.models import Firm
        
        result = await db.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]
        
        for tenant_id in tenant_ids:
            await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            
            repository = OutboxRepository(db, tenant_id)
            events = await repository.get_pending_events(
                event_types=[
                    OutboxEventType.DOCUMENT_UPLOADED,
                    OutboxEventType.DOCUMENT_PROCESSED,
                    OutboxEventType.DOCUMENT_CLASSIFIED,
                ],
                limit=100,
            )
            
            for event in events:
                try:
                    if event.event_type in [OutboxEventType.DOCUMENT_UPLOADED, OutboxEventType.DOCUMENT_PROCESSED, OutboxEventType.DOCUMENT_CLASSIFIED]:
                        document_id = event.payload.get("document_id")
                        if document_id:
                            index_document_task.delay(str(tenant_id), document_id)
                    
                    await repository.mark_event_processed(event.id)
                    
                except Exception as e:
                    logger.error("Search index queue processing failed", event_id=str(event.id), error=str(e))
                    await repository.mark_event_failed(event.id, str(e))
            
            await db.commit()