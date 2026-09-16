from .manager import OpenSearchManager, OpenSearchService, get_opensearch, close_opensearch
from .schemas import (
    OpenSearchDocumentCreate,
    OpenSearchDocumentUpdate,
    OpenSearchDocumentResponse,
    OpenSearchSearchRequest,
    OpenSearchSearchResponse,
    OpenSearchBulkIndexRequest,
    OpenSearchBulkIndexResponse,
    CommunicationSearchRequest,
    CommunicationSearchResponse,
    AIProcessingJobSearchRequest,
    AIProcessingJobSearchResponse,
    OpenSearchHealthResponse,
)

__all__ = [
    "OpenSearchManager",
    "OpenSearchService",
    "get_opensearch",
    "close_opensearch",
    "OpenSearchDocumentCreate",
    "OpenSearchDocumentUpdate",
    "OpenSearchDocumentResponse",
    "OpenSearchSearchRequest",
    "OpenSearchSearchResponse",
    "OpenSearchBulkIndexRequest",
    "OpenSearchBulkIndexResponse",
    "CommunicationSearchRequest",
    "CommunicationSearchResponse",
    "AIProcessingJobSearchRequest",
    "AIProcessingJobSearchResponse",
    "OpenSearchHealthResponse",
]