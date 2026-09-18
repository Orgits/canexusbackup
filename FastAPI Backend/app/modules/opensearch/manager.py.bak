from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from opensearchpy import AsyncOpenSearch
from opensearchpy.helpers import async_bulk

from app.core.config import get_settings


class OpenSearchManager:
    def __init__(self):
        self._client: Optional[AsyncOpenSearch] = None
        self._settings = get_settings()

    async def connect(self):
        """Initialize OpenSearch connection."""
        self._client = AsyncOpenSearch(
            hosts=[self._settings.OPENSEARCH_URL],
            http_auth=(self._settings.OPENSEARCH_USERNAME, self._settings.OPENSEARCH_PASSWORD) if self._settings.OPENSEARCH_USERNAME else None,
            use_ssl=self._settings.OPENSEARCH_USE_SSL,
            verify_certs=self._settings.OPENSEARCH_VERIFY_CERTS,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )

        # Create index templates
        await self._create_index_templates()

    async def disconnect(self):
        """Close OpenSearch connection."""
        if self._client:
            await self._client.close()

    async def _create_index_templates(self):
        """Create index templates for different document types."""
        if not self._client:
            return

        # Document index template
        doc_template = {
            "index_patterns": ["documents-*"],
            "template": {
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1,
                    "refresh_interval": "5s",
                },
                "mappings": {
                    "properties": {
                        "tenant_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "title": {"type": "text", "analyzer": "standard"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "extracted_text": {"type": "text", "analyzer": "standard"},
                        "structured_data": {"type": "object", "enabled": True},
                        "metadata": {"type": "object", "enabled": True},
                        "tags": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        "created_by": {"type": "keyword"},
                        "client_id": {"type": "keyword"},
                        "matter_id": {"type": "keyword"},
                    }
                }
            }

        # Communications index template
        comm_template = {
            "index_patterns": ["communications-*"],
            "template": {
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                },
                "mappings": {
                    "properties": {
                        "tenant_id": {"type": "keyword"},
                        "communication_id": {"type": "keyword"},
                        "channel": {"type": "keyword"},
                        "direction": {"type": "keyword"},
                        "subject": {"type": "text", "analyzer": "standard"},
                        "body": {"type": "text", "analyzer": "standard"},
                        "from_address": {"type": "keyword"},
                        "to_addresses": {"type": "keyword"},
                        "thread_id": {"type": "keyword"},
                        "conversation_id": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "sent_at": {"type": "date"},
                        "delivered_at": {"type": "date"},
                        "read_at": {"type": "date"},
                    }
                }
            }

        # AI Processing index template
        ai_template = {
            "index_patterns": ["ai-processing-*"],
            "template": {
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                },
                "mappings": {
                    "properties": {
                        "tenant_id": {"type": "keyword"},
                        "job_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "model_id": {"type": "keyword"},
                        "model_type": {"type": "keyword"},
                        "input_data": {"type": "object", "enabled": True},
                        "output_data": {"type": "object", "enabled": True},
                        "confidence_score": {"type": "float"},
                        "processing_time_ms": {"type": "integer"},
                        "tokens_used": {"type": "integer"},
                        "cost": {"type": "float"},
                        "status": {"type": "keyword"},
                    }
                }
            }

        # Webhook events index template
        webhook_template = {
            "index_patterns": ["webhook-events-*"],
            "template": {
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                },
                "mappings": {
                    "properties": {
                        "tenant_id": {"type": "keyword"},
                        "event_id": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "event_type": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "processed_at": {"type": "date"},
                    }
                }
            }

        # Try to create templates (ignore if they exist)
        try:
            await self._client.indices.put_index_template(name="documents-template", body=doc_template)
            await self._client.indices.put_index_template(name="communications-template", body=comm_template)
            await self._client.indices.put_index_template(name="ai-processing-template", body=ai_template)
            await self._client.indices.put_index_template(name="webhook-events-template", body=webhook_template)
        except Exception:
            # Templates might already exist
            pass

    @property
    def client(self) -> AsyncOpenSearch:
        if not self._client:
            raise RuntimeError("OpenSearch not connected")
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()


class OpenSearchService:
    """Service for indexing and searching documents in OpenSearch."""

    def __init__(self, client: AsyncOpenSearch):
        self.client = client

    def _get_index_name(self, base_name: str, tenant_id: str) -> str:
        """Get index name with tenant partitioning."""
        return f"{base_name}-{tenant_id}"

    # Document indexing
    async def index_document(
        self,
        tenant_id: str,
        document_id: str,
        title: str,
        content: str,
        extracted_text: str | None = None,
        structured_data: dict | None = None,
        metadata: dict | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        status: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        created_by: str | None = None,
        client_id: str | None = None,
        matter_id: str | None = None,
    ) -> dict:
        """Index a document in OpenSearch."""
        index_name = f"documents-{tenant_id}"

        doc = {
            "document_id": document_id,
            "title": title,
            "content": content,
            "extracted_text": extracted_text,
            "structured_data": structured_data or {},
            "metadata": metadata or {},
            "tags": tags or [],
            "category": category,
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
            "client_id": client_id,
            "matter_id": matter_id,
        }

        result = await self.client.index(
            index=self._get_index_name("documents", tenant_id),
            id=document_id,
            body=doc,
            refresh="wait_for",
        )
        return result

    async def update_document(self, tenant_id: str, document_id: str, updates: dict) -> dict:
        """Update a document in OpenSearch."""
        index_name = f"documents-{tenant_id}"

        # Add updated_at
        updates["updated_at"] = datetime.utcnow().isoformat()

        result = await self.client.update(
            index=self._get_index_name("documents", tenant_id),
            id=document_id,
            body={"doc": updates},
            refresh="wait_for",
        )
        return result

    async def delete_document(self, tenant_id: str, document_id: str) -> dict:
        """Delete a document from OpenSearch."""
        result = await self.client.delete(
            index=self._get_index_name("documents", tenant_id),
            id=document_id,
            refresh="wait_for",
        )
        return result

    async def search_documents(
        self,
        tenant_id: str,
        query: str | None = None,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> dict:
        """Search documents in OpenSearch."""
        index_name = self._get_index_name("documents", tenant_id)

        # Build query
        query_body = {
            "size": page_size,
            "from": (page - 1) * page_size,
            "query": {},
            "sort": [],
        }

        # Build query
        must_clauses = []

        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content^2", "extracted_text", "tags", "metadata.*"],
                    "type": "best_fields",
                }
            })

        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    must_clauses.append({"terms": {field: value}})
                else:
                    must_clauses.append({"term": {field: value}})

        if must_clauses:
            query_body["query"] = {"bool": {"must": must_clauses}}
        else:
            query_body["query"] = {"match_all": {}}

        # Add sorting
        if sort_by:
            sort_field = sort_by
            sort_direction = sort_order
            query_body["sort"] = [{sort_field: {"order": sort_direction}}]
        else:
            query_body["sort"] = [{"updated_at": {"order": "desc"}}]

        result = await self.client.search(index=self._get_index_name("documents", tenant_id), body=query_body)
        return result

    async def bulk_index_documents(self, tenant_id: str, documents: list[dict]) -> dict:
        """Bulk index multiple documents."""
        actions = []
        for doc in documents:
            doc_id = doc.pop("document_id", doc.pop("id", None))
            if not doc_id:
                continue

            action = {
                "_op_type": "index",
                "_index": self._get_index_name("documents", tenant_id),
                "_id": doc_id,
                "_source": doc,
            }
            actions.append(action)

        if actions:
            result = await self.client.bulk(body=actions, refresh="wait_for")
            return result

        return {"errors": False, "items": []}

    # Communication indexing
    async def index_communication(
        self,
        tenant_id: str,
        communication_id: str,
        channel: str,
        direction: str,
        subject: str | None,
        body: str,
        from_address: str | None,
        to_addresses: list[str] | None = None,
        thread_id: str | None = None,
        conversation_id: str | None = None,
        status: str | None = None,
        sent_at: datetime | None = None,
        delivered_at: datetime | None = None,
        read_at: datetime | None = None,
        client_id: str | None = None,
        matter_id: str | None = None,
    ) -> dict:
        """Index a communication in OpenSearch."""
        doc = {
            "communication_id": communication_id,
            "channel": channel,
            "direction": direction,
            "subject": subject,
            "body": body,
            "from_address": from_address,
            "to_addresses": to_addresses or [],
            "thread_id": thread_id,
            "conversation_id": conversation_id,
            "status": status,
            "sent_at": sent_at.isoformat() if sent_at else None,
            "delivered_at": delivered_at.isoformat() if delivered_at else None,
            "read_at": read_at.isoformat() if read_at else None,
            "client_id": client_id,
            "matter_id": matter_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = await self.client.index(
            index=self._get_index_name("communications", tenant_id),
            id=communication_id,
            body=doc,
            refresh="wait_for",
        )
        return result

    async def search_communications(
        self,
        tenant_id: str,
        query: str | None = None,
        channel: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search communications in OpenSearch."""
        index_name = self._get_index_name("communications", tenant_id)

        must_clauses = []

        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["subject^3", "body^2", "from_address", "to_addresses"],
                }
            })

        if channel:
            must_clauses.append({"term": {"channel": channel}})

        if direction:
            must_clauses.append({"term": {"direction": direction}})

        if status:
            must_clauses.append({"term": {"status": status}})

        if date_from:
            must_clauses.append({"range": {"sent_at": {"gte": date_from.isoformat()}}})

        if date_to:
            must_clauses.append({"range": {"sent_at": {"lte": date_to.isoformat()}}})

        query_body = {
            "size": page_size,
            "from": (page - 1) * page_size,
            "query": {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}},
            "sort": [{"sent_at": {"order": "desc"}}],
        }

        result = await self.client.search(index=self._get_index_name("communications", tenant_id), body=query_body)
        return result

    # AI Processing indexing
    async def index_ai_job(
        self,
        tenant_id: str,
        job_id: str,
        document_id: str,
        model_id: str,
        model_type: str,
        input_data: dict,
        output_data: dict | None = None,
        confidence_score: float | None = None,
        processing_time_ms: int | None = None,
        tokens_used: int | None = None,
        cost: float | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ) -> dict:
        """Index an AI processing job in OpenSearch."""
        doc = {
            "job_id": job_id,
            "document_id": document_id,
            "model_id": model_id,
            "model_type": model_type,
            "input_data": input_data,
            "output_data": output_data or {},
            "confidence_score": confidence_score,
            "processing_time_ms": processing_time_ms,
            "tokens_used": tokens_used,
            "cost": cost,
            "status": status,
            "error_message": error_message,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = await self.client.index(
            index=self._get_index_name("ai-processing", tenant_id),
            id=job_id,
            body=doc,
            refresh="wait_for",
        )
        return result

    async def search_ai_jobs(
        self,
        tenant_id: str,
        query: str | None = None,
        model_type: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search AI processing jobs."""
        index_name = self._get_index_name("ai-processing", tenant_id)

        must_clauses = []

        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["input_data", "output_data"],
                }
            })

        if model_type:
            must_clauses.append({"term": {"model_type": model_type}})

        if status:
            must_clauses.append({"term": {"status": status}})

        if date_from:
            must_clauses.append({"range": {"created_at": {"gte": date_from.isoformat()}}})

        if date_to:
            must_clauses.append({"range": {"created_at": {"lte": date_to.isoformat()}}})

        query_body = {
            "size": page_size,
            "from": (page - 1) * page_size,
            "query": {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}},
            "sort": [{"created_at": {"order": "desc"}}],
        }

        result = await self.client.search(index=self._get_index_name("ai-processing", tenant_id), body=query_body)
        return result


# Global instance
_opensearch_manager: OpenSearchManager | None = None


async def get_opensearch() -> OpenSearchManager:
    """Get or create OpenSearch manager instance."""
    global _opensearch_manager
    if _opensearch_manager is None:
        _opensearch_manager = OpenSearchManager()
        await _opensearch_manager.connect()
    return _opensearch_manager


async def close_opensearch():
    """Close OpenSearch connection."""
    global _opensearch_manager
    if _opensearch_manager:
        await _opensearch_manager.disconnect()
        _opensearch_manager = None