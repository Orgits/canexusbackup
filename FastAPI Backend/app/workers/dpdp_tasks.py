import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy import select, and_, func

from app.core.celery.app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.core.storage.azure_blob import get_azure_blob_service
from app.modules.dpdp.models import (
    DataAccessRequest,
    DataCorrectionRequest,
    DataErasureRequest,
    RetentionPolicy,
    RetentionExecution,
    DataAccessStatus,
    DataErasureStatus,
    RetentionAction,
)
from app.modules.dpdp.repository import DPDPRepository
from app.modules.outbox.service import OutboxService
from app.modules.outbox.models import OutboxEventType

logger = get_logger(__name__)


async def _get_tenant_db(tenant_id: UUID):
    """Get a database session with tenant context set."""
    async with AsyncSessionLocal() as db:
        await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        yield db


@shared_task(bind=True, max_retries=3, default_retry_delay=300, autoretry_for=(Exception,))
def process_data_erasure_task(self, request_id: str):
    """Process a data erasure request asynchronously."""
    request_uuid = UUID(request_id)
    return asyncio.run(_process_data_erasure_async(request_uuid))


async def _process_data_erasure_async(request_id: UUID):
    async with AsyncSessionLocal() as db:
        repository = DPDPRepository(db, None)
        request = await repository.get_data_erasure_request(request_id)
        
        if not request:
            logger.error("Data erasure request not found", request_id=str(request_id))
            return

        tenant_id = request.tenant_id
        await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

        try:
            request.status = DataErasureStatus.IN_PROGRESS
            request.started_at = datetime.utcnow()
            await db.flush()

            scope = request.scope
            entities_to_erase = scope.get("entities", [])
            
            total_affected = 0

            for entity_spec in entities_to_erase:
                entity_type = entity_spec.get("type")
                entity_ids = entity_spec.get("ids", [])
                criteria = entity_spec.get("criteria", {})

                affected = await _erase_entity_data(db, tenant_id, entity_type, entity_ids, criteria)
                total_affected += affected

            request.entities_affected = total_affected
            request.status = DataErasureStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.verification_token = secrets.token_urlsafe(32)
            await db.flush()

            await _emit_erasure_completed_event(db, request, total_affected)

            logger.info("Data erasure completed", request_id=str(request_id), entities_affected=total_affected)

        except Exception as e:
            logger.error("Data erasure failed", request_id=str(request_id), error=str(e))
            request.status = DataErasureStatus.FAILED
            request.error_message = str(e)
            request.error_details = {"exception": type(e).__name__}
            request.completed_at = datetime.utcnow()
            await db.flush()

            if self.request.retries < self.max_retries:
                raise self.retry(exc=e)
            
            request.status = DataErasureStatus.FAILED
            request.error_details = {"exception": type(e).__name__, "max_retries_exceeded": True}
            await db.flush()

        await db.commit()


async def _erase_entity_data(
    db,
    tenant_id: UUID,
    entity_type: str,
    entity_ids: list[str],
    criteria: dict
) -> int:
    """Erase data for a specific entity type."""
    model_map = {
        "Client": "app.modules.clients.models.Client",
        "Matter": "app.modules.matters.models.Matter",
        "Task": "app.modules.tasks.models.Task",
        "Document": "app.modules.documents.models.Document",
        "Invoice": "app.modules.billing.models.Invoice",
        "Payment": "app.modules.billing.models.Payment",
        "Expense": "app.modules.billing.models.Expense",
        "Communication": "app.modules.communications.models.Communication",
        "ComplianceCycle": "app.modules.compliance.models.ComplianceCycle",
    }

    if entity_type not in model_map:
        logger.warning("Unknown entity type for erasure", entity_type=entity_type)
        return 0

    module_path, class_name = model_map[entity_type].rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    Model = getattr(module, class_name)

    query = select(Model).where(Model.tenant_id == tenant_id)

    if entity_ids:
        uuid_ids = [UUID(eid) for eid in entity_ids]
        query = query.where(Model.id.in_(uuid_ids))
    else:
        for field, value in criteria.items():
            if hasattr(Model, field):
                query = query.where(getattr(Model, field) == value)

    if criteria.get("before_date"):
        if hasattr(Model, "created_at"):
            query = query.where(Model.created_at < criteria["before_date"])

    result = await db.execute(query)
    entities = result.scalars().all()

    affected = 0
    for entity in entities:
        if hasattr(entity, "status"):
            entity.status = "ERASED"
        if hasattr(entity, "is_deleted"):
            entity.is_deleted = True
        
        for attr in dir(entity):
            if not attr.startswith("_") and attr not in ("id", "tenant_id", "created_at", "updated_at", "created_by_id", "updated_by_id"):
                try:
                    value = getattr(entity, attr)
                    if value is not None:
                        setattr(entity, attr, None)
                except Exception:
                    pass
        
        affected += 1

    await db.flush()
    return affected


async def _emit_erasure_completed_event(db, request: DataErasureRequest, entities_affected: int):
    """Emit outbox event for erasure completion."""
    outbox_service = OutboxService(db)
    await outbox_service.create_event(
        event_type=OutboxEventType.DATA_ERASURE_COMPLETED,
        aggregate_type="data_erasure_request",
        aggregate_id=request.id,
        payload={
            "request_id": str(request.id),
            "subject_id": str(request.subject_id),
            "entities_affected": entities_affected,
            "verification_token": request.verification_token,
        },
        tenant_id=request.tenant_id,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=300, autoretry_for=(Exception,))
def compile_data_access_task(self, request_id: str):
    """Compile data for a data access request asynchronously."""
    request_uuid = UUID(request_id)
    return asyncio.run(_compile_data_access_async(request_uuid))


async def _compile_data_access_async(request_id: UUID):
    async with AsyncSessionLocal() as db:
        repository = DPDPRepository(db, None)
        request = await repository.get_data_access_request(request_id)
        
        if not request:
            logger.error("Data access request not found", request_id=str(request_id))
            return

        tenant_id = request.tenant_id
        await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

        try:
            request.status = DataAccessStatus.COMPILING
            await db.flush()

            scope = request.scope
            entities_to_include = scope.get("entities", [])
            
            compiled_data = {}

            for entity_spec in entities_to_include:
                entity_type = entity_spec.get("type")
                entity_ids = entity_spec.get("ids", [])
                criteria = entity_spec.get("criteria", {})

                data = await _collect_entity_data(db, tenant_id, entity_type, entity_ids, criteria)
                compiled_data[entity_type] = data

            import json
            json_data = json.dumps(compiled_data, default=str).encode("utf-8")
            
            blob_service = get_azure_blob_service()
            storage_key = f"{tenant_id}/data-access/{request_id}/export.json"
            
            await blob_service.upload_blob(
                storage_key=storage_key,
                data=json_data,
                content_type="application/json",
            )

            import hashlib
            checksum = hashlib.sha256(json_data).hexdigest()

            request.compiled_data_ref = storage_key
            request.compiled_size = len(json_data)
            request.compiled_checksum = checksum
            request.status = DataAccessStatus.READY
            request.expires_at = datetime.utcnow() + timedelta(days=7)
            await db.flush()

            logger.info("Data access compilation completed", request_id=str(request_id), size=len(json_data))

        except Exception as e:
            logger.error("Data access compilation failed", request_id=str(request_id), error=str(e))
            request.status = DataAccessStatus.FAILED
            request.error_message = str(e)
            await db.flush()

            if self.request.retries < self.max_retries:
                raise self.retry(exc=e)
            
            request.status = DataAccessStatus.FAILED
            await db.flush()

        await db.commit()


async def _collect_entity_data(
    db,
    tenant_id: UUID,
    entity_type: str,
    entity_ids: list[str],
    criteria: dict
) -> list[dict]:
    """Collect data for a specific entity type."""
    model_map = {
        "Client": "app.modules.clients.models.Client",
        "Matter": "app.modules.matters.models.Matter",
        "Task": "app.modules.tasks.models.Task",
        "Document": "app.modules.documents.models.Document",
        "Invoice": "app.modules.billing.models.Invoice",
        "Payment": "app.modules.billing.models.Payment",
        "Expense": "app.modules.billing.models.Expense",
        "Communication": "app.modules.communications.models.Communication",
        "ComplianceCycle": "app.modules.compliance.models.ComplianceCycle",
    }

    if entity_type not in model_map:
        return []

    module_path, class_name = model_map[entity_type].rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    Model = getattr(module, class_name)

    query = select(Model).where(Model.tenant_id == tenant_id)

    if entity_ids:
        uuid_ids = [UUID(eid) for eid in entity_ids]
        query = query.where(Model.id.in_(uuid_ids))
    else:
        for field, value in criteria.items():
            if hasattr(Model, field):
                query = query.where(getattr(Model, field) == value)

    if criteria.get("before_date"):
        if hasattr(Model, "created_at"):
            query = query.where(Model.created_at < criteria["before_date"])

    result = await db.execute(query)
    entities = result.scalars().all()

    data = []
    for entity in entities:
        entity_dict = {}
        for attr in dir(entity):
            if not attr.startswith("_") and not callable(getattr(entity.__class__, attr, None)):
                try:
                    value = getattr(entity, attr)
                    if hasattr(value, "isoformat"):
                        entity_dict[attr] = value.isoformat()
                    elif isinstance(value, UUID):
                        entity_dict[attr] = str(value)
                    else:
                        entity_dict[attr] = value
                except Exception:
                    pass
        data.append(entity_dict)

    return data


@shared_task
def execute_retention_policies():
    """Execute all due retention policies - called by Celery Beat."""
    return asyncio.run(_execute_retention_policies_async())


async def _execute_retention_policies_async():
    async with AsyncSessionLocal() as db:
        from app.modules.firms.models import Firm
        
        result = await db.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]
        
        total_executed = 0
        
        for tenant_id in tenant_ids:
            await db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            
            repository = DPDPRepository(db, tenant_id)
            
            policies, _ = await repository.list_retention_policies(is_active=True, page_size=1000)
            
            for policy in policies:
                try:
                    execution = RetentionExecution(
                        policy_id=policy.id,
                        status="processing",
                        started_at=datetime.utcnow(),
                        tenant_id=tenant_id,
                    )
                    db.add(execution)
                    await db.flush()

                    affected = await _execute_single_policy(db, tenant_id, policy)
                    
                    execution.status = "completed"
                    execution.entities_affected = affected
                    execution.entities_processed = affected
                    execution.completed_at = datetime.utcnow()
                    await db.flush()

                    await _emit_retention_executed_event(db, execution, policy, affected)
                    
                    total_executed += 1
                    
                except Exception as e:
                    logger.error("Retention policy execution failed", policy_id=str(policy.id), error=str(e))
                    
                    execution = RetentionExecution(
                        policy_id=policy.id,
                        status="failed",
                        error_message=str(e),
                        error_details={"exception": type(e).__name__},
                        executed_at=datetime.utcnow(),
                        tenant_id=tenant_id,
                    )
                    db.add(execution)
                    await db.flush()
            
            await db.commit()
        
        logger.info("Retention policies execution completed", total_policies=total_executed)


async def _execute_single_policy(db, tenant_id: UUID, policy: RetentionPolicy) -> int:
    """Execute a single retention policy."""
    model_map = {
        "Client": "app.modules.clients.models.Client",
        "Matter": "app.modules.matters.models.Matter",
        "Task": "app.modules.tasks.models.Task",
        "Document": "app.modules.documents.models.Document",
        "Invoice": "app.modules.billing.models.Invoice",
        "Payment": "app.modules.billing.models.Payment",
        "Expense": "app.modules.billing.models.Expense",
        "Communication": "app.modules.communications.models.Communication",
        "ComplianceCycle": "app.modules.compliance.models.ComplianceCycle",
    }

    if policy.entity_type not in model_map:
        logger.warning("Unknown entity type for retention", entity_type=policy.entity_type)
        return 0

    module_path, class_name = model_map[policy.entity_type].rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    Model = getattr(module, class_name)

    cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
    
    query = select(Model).where(
        and_(
            Model.tenant_id == tenant_id,
            Model.created_at < cutoff_date,
        )
    )

    criteria = policy.criteria
    for field, value in criteria.items():
        if hasattr(Model, field):
            query = query.where(getattr(Model, field) == value)

    if policy.protected:
        protected_ids = criteria.get("protected_ids", [])
        if protected_ids:
            uuid_ids = [UUID(pid) for pid in protected_ids]
            query = query.where(Model.id.notin_(uuid_ids))

    result = await db.execute(query)
    entities = result.scalars().all()

    affected = 0
    for entity in entities:
        if policy.action == RetentionAction.DELETE:
            await db.delete(entity)
        elif policy.action == RetentionAction.ARCHIVE:
            if hasattr(entity, "status"):
                entity.status = "ARCHIVED"
            if hasattr(entity, "is_archived"):
                entity.is_archived = True
        elif policy.action == RetentionAction.ANONYMIZE:
            for attr in dir(entity):
                if not attr.startswith("_") and attr not in ("id", "tenant_id", "created_at", "updated_at"):
                    try:
                        value = getattr(entity, attr)
                        if value is not None and isinstance(value, (str, int, float, bool)):
                            setattr(entity, attr, None)
                    except Exception:
                        pass
        
        affected += 1

    await db.flush()
    return affected


async def _emit_retention_executed_event(db, execution: RetentionExecution, policy: RetentionPolicy, affected: int):
    """Emit outbox event for retention execution."""
    outbox_service = OutboxService(db)
    await outbox_service.create_event(
        event_type=OutboxEventType.RETENTION_EXECUTED,
        aggregate_type="retention_policy",
        aggregate_id=policy.id,
        payload={
            "execution_id": str(execution.id),
            "policy_id": str(policy.id),
            "policy_name": policy.name,
            "entity_type": policy.entity_type,
            "entities_affected": affected,
            "action": policy.action.value,
        },
        tenant_id=execution.tenant_id,
    )