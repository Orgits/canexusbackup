from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.tenancy import get_tenant_context, TenantContext
from app.modules.opensearch.manager import get_opensearch, OpenSearchService

router = APIRouter()


async def get_opensearch_service() -> OpenSearchService:
    manager = await get_opensearch()
    return OpenSearchService(manager.client)


@router.get("/global", dependencies=[Depends(require_permission("search.global"))])
async def global_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types: documents,communications,ai-jobs"),
    client_id: Optional[UUID] = Query(None),
    matter_id: Optional[UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    search_service: OpenSearchService = Depends(get_opensearch_service),
):
    """
    Global search across all indexed entities for the current tenant.
    
    Entity types:
    - documents: Search documents by title, content, extracted text, tags
    - communications: Search communications by subject, body, addresses
    - ai-jobs: Search AI processing jobs by input/output data
    """
    tenant_id = str(tenant_context.tenant_id)
    
    types = entity_types.split(",") if entity_types else ["documents", "communications", "ai-jobs"]
    
    results = {}
    total_hits = 0
    
    for entity_type in types:
        if entity_type == "documents":
            result = await search_service.search_documents(
                tenant_id=tenant_id,
                query=q,
                filters={
                    "client_id": str(client_id) if client_id else None,
                    "matter_id": str(matter_id) if matter_id else None,
                } if client_id or matter_id else None,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        elif entity_type == "communications":
            result = await search_service.search_communications(
                tenant_id=tenant_id,
                query=q,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size,
            )
        elif entity_type == "ai-jobs":
            result = await search_service.search_ai_jobs(
                tenant_id=tenant_id,
                query=q,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size,
            )
        else:
            continue
        
        hits = result.get("hits", {}).get("hits", [])
        total = result.get("hits", {}).get("total", {}).get("value", 0)
        
        results[entity_type] = {
            "hits": [
                {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "source": hit["_source"],
                }
                for hit in hits
            ],
            "total": total,
        }
        total_hits += total
    
    return {
        "query": q,
        "tenant_id": tenant_id,
        "total_hits": total_hits,
        "page": page,
        "page_size": page_size,
        "results": results,
    }


@router.get("/documents", dependencies=[Depends(require_permission("search.global"))])
async def search_documents(
    q: Optional[str] = Query(None),
    client_id: Optional[UUID] = Query(None),
    matter_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    search_service: OpenSearchService = Depends(get_opensearch_service),
):
    """Search documents with advanced filters."""
    tenant_id = str(tenant_context.tenant_id)
    
    filters = {}
    if client_id:
        filters["client_id"] = str(client_id)
    if matter_id:
        filters["matter_id"] = str(matter_id)
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status
    if tags:
        filters["tags"] = tags.split(",")
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    
    result = await search_service.search_documents(
        tenant_id=tenant_id,
        query=q,
        filters=filters if filters else None,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    return {
        "query": q,
        "tenant_id": tenant_id,
        "total": result.get("hits", {}).get("total", {}).get("value", 0),
        "page": page,
        "page_size": page_size,
        "hits": [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                "source": hit["_source"],
            }
            for hit in result.get("hits", {}).get("hits", [])
        ],
    }


@router.get("/communications", dependencies=[Depends(require_permission("search.global"))])
async def search_communications(
    q: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_context: TenantContext = Depends(get_tenant_context),
    search_service: OpenSearchService = Depends(get_opensearch_service),
):
    """Search communications with filters."""
    tenant_id = str(tenant_context.tenant_id)
    
    result = await search_service.search_communications(
        tenant_id=tenant_id,
        query=q,
        channel=channel,
        direction=direction,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    
    return {
        "query": q,
        "tenant_id": tenant_id,
        "total": result.get("hits", {}).get("total", {}).get("value", 0),
        "page": page,
        "page_size": page_size,
        "hits": [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                "source": hit["_source"],
            }
            for hit in result.get("hits", {}).get("hits", [])
        ],
    }


@router.get("/ai-jobs", dependencies=[Depends(require_permission("search.global"))])
async def search_ai_jobs(
    q: Optional[str] = Query(None),
    model_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_context: TenantContext = Depends(get_tenant_context),
    search_service: OpenSearchService = Depends(get_opensearch_service),
):
    """Search AI processing jobs."""
    tenant_id = str(tenant_context.tenant_id)
    
    result = await search_service.search_ai_jobs(
        tenant_id=tenant_id,
        query=q,
        model_type=model_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    
    return {
        "query": q,
        "tenant_id": tenant_id,
        "total": result.get("hits", {}).get("total", {}).get("value", 0),
        "page": page,
        "page_size": page_size,
        "hits": [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                "source": hit["_source"],
            }
            for hit in result.get("hits", {}).get("hits", [])
        ],
    }


@router.post("/reindex/{entity_type}", dependencies=[Depends(require_permission("search.global"))])
async def trigger_reindex(
    entity_type: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    """Trigger a reindex for a specific entity type (admin only)."""
    from app.workers.search_indexer_tasks import reindex_entity_type_task
    
    if entity_type not in ["documents", "communications", "ai-jobs"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
    
    reindex_entity_type_task.delay(str(tenant_context.tenant_id), entity_type)
    
    return {"message": f"Reindex triggered for {entity_type}", "tenant_id": str(tenant_context.tenant_id)}