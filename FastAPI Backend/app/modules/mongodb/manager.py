from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING, Any, Optional

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.database import Database
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.modules.users.models import User


class MongoDBManager:
    def __init__(self):
        self._client = None
        self._db: AsyncIOMotorDatabase | None = None

    async def connect(self):
        """Initialize MongoDB connection."""
        from motor.motor_asyncio import AsyncIOMotorClient

        settings = get_settings()
        self._client = AsyncIOMotorClient(settings.MONGODB_URL)
        self._db = self._client[settings.MONGODB_DATABASE]

        # Create indexes
        await self._create_indexes()

    async def disconnect(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()

    async def _create_indexes(self):
        """Create necessary indexes for collections."""
        if not self._db:
            return

        # Raw payloads collection
        raw_payloads = self._db.raw_payloads
        await raw_payloads.create_indexes([
            IndexModel([("tenant_id", ASCENDING), ("source", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("document_id", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("received_at", DESCENDING)]),
            IndexModel([("idempotency_key", ASCENDING)], unique=True),
        ])

        # Document raw content
        doc_raw = self._db.document_raw
        await doc_raw.create_indexes([
            IndexModel([("tenant_id", ASCENDING), ("document_id", ASCENDING)], unique=True),
            IndexModel([("tenant_id", ASCENDING), ("created_at", DESCENDING)]),
        ])

        # AI processing raw payloads
        ai_raw = self._db.ai_raw_payloads
        await ai_raw.create_indexes([
            IndexModel([("tenant_id", ASCENDING), ("job_id", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("created_at", DESCENDING)]),
        ])

        # Webhook raw payloads
        webhook_raw = self._db.webhook_raw
        await webhook_raw.create_indexes([
            IndexModel([("tenant_id", ASCENDING), ("source", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("external_id", ASCENDING)], unique=True),
            IndexModel([("tenant_id", ASCENDING), ("received_at", DESCENDING)]),
        ])

    def get_collection(self, name: str) -> Collection:
        """Get a collection by name."""
        if not self._db:
            raise RuntimeError("MongoDB not connected")
        return self._db[name]

    @property
    def db(self) -> Database:
        if not self._db:
            raise RuntimeError("MongoDB not connected")
        return self._db

    @property
    def raw_payloads(self) -> Collection:
        return self.db.raw_payloads

    @property
    def document_raw(self) -> Collection:
        return self.db.document_raw

    @property
    def ai_raw_payloads(self) -> Collection:
        return self.db.ai_raw_payloads

    @property
    def webhook_raw(self) -> Collection:
        return self.db.webhook_raw


# Global instance
_mongodb_manager: MongoDBManager | None = None


async def get_mongodb() -> MongoDBManager:
    """Get or create MongoDB manager instance."""
    global _mongodb_manager
    if _mongodb_manager is None:
        _mongodb_manager = MongoDBManager()
        await _mongodb_manager.connect()
    return _mongodb_manager


async def close_mongodb():
    """Close MongoDB connection."""
    global _mongodb_manager
    if _mongodb_manager:
        await _mongodb_manager.disconnect()
        _mongodb_manager = None


class RawPayloadService:
    """Service for storing and retrieving raw payloads in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def store_raw_payload(
        self,
        tenant_id: UUID,
        source: str,
        payload: dict,
        document_id: UUID | None = None,
        idempotency_key: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Store a raw payload in MongoDB."""
        collection = self.db.raw_payloads

        doc = {
            "tenant_id": str(tenant_id),
            "source": source,
            "payload": payload,
            "document_id": str(document_id) if document_id else None,
            "idempotency_key": idempotency_key,
            "metadata": metadata or {},
            "received_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }

        # Use idempotency key for upsert if provided
        if idempotency_key:
            result = await self.db.raw_payloads.update_one(
                {"idempotency_key": idempotency_key, "tenant_id": str(tenant_id)},
                {"$setOnInsert": doc},
                upsert=True,
            )
            if result.upserted_id:
                doc["_id"] = result.upserted_id
            return doc

        result = await self.db.raw_payloads.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_raw_payload(
        self,
        payload_id: str,
        tenant_id: UUID,
    ) -> dict | None:
        """Retrieve a raw payload by ID."""
        from bson import ObjectId
        collection = self.db.raw_payloads
        return await collection.find_one({"_id": ObjectId(payload_id), "tenant_id": str(tenant_id)})

    async def get_payloads_by_document(
        self,
        document_id: UUID,
        tenant_id: UUID,
    ) -> list[dict]:
        """Get all raw payloads for a document."""
        collection = self.db.raw_payloads
        cursor = collection.find({
            "tenant_id": str(tenant_id),
            "document_id": str(document_id),
        }).sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def get_payloads_by_source(
        self,
        tenant_id: UUID,
        source: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get raw payloads by source."""
        collection = self.db.raw_payloads
        cursor = collection.find({
            "tenant_id": str(tenant_id),
            "source": source,
        }).sort("created_at", -1).skip(offset).limit(limit)
        return await cursor.to_list(length=None)


class DocumentRawService:
    """Service for storing raw document content in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def store_document_raw(
        self,
        tenant_id: UUID,
        document_id: UUID,
        content: str,
        extracted_data: dict | None = None,
        ocr_result: dict | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Store raw document content."""
        collection = self.db.document_raw

        doc = {
            "tenant_id": str(tenant_id),
            "document_id": str(document_id),
            "content": content,
            "extracted_data": extracted_data or {},
            "ocr_result": ocr_result or {},
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await self.db.document_raw.update_one(
            {"tenant_id": str(tenant_id), "document_id": str(document_id)},
            {"$set": doc},
            upsert=True,
        )

        doc["_id"] = result.upserted_id or (await self.db.document_raw.find_one({"tenant_id": str(tenant_id), "document_id": str(document_id)}))["_id"]
        return doc

    async def get_document_raw(self, document_id: UUID, tenant_id: UUID) -> dict | None:
        """Get raw document content."""
        collection = self.db.document_raw
        return await collection.find_one({"tenant_id": str(tenant_id), "document_id": str(document_id)})

    async def update_document_raw(
        self,
        document_id: UUID,
        tenant_id: UUID,
        updates: dict,
    ) -> dict | None:
        """Update raw document content."""
        collection = self.db.document_raw
        updates["updated_at"] = datetime.utcnow()
        result = await collection.update_one(
            {"tenant_id": str(tenant_id), "document_id": str(document_id)},
            {"$set": updates},
        )
        if result.modified_count:
            return await collection.find_one({"tenant_id": str(tenant_id), "document_id": str(document_id)})
        return None