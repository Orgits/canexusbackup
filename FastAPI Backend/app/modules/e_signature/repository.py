from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.e_signature.models import (
    ESignatureRequest,
    ESigner,
    ESignatureProviderConfig,
    ESignatureWebhookEvent,
    ESignatureRequestStatus,
    ESignerStatus,
    ESignatureProvider,
)


class ESignatureRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: ESignatureRequest) -> ESignatureRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> ESignatureRequest | None:
        result = await self.db.execute(
            select(ESignatureRequest)
            .options(
                selectinload(ESignatureRequest.document),
                selectinload(ESignatureRequest.engagement_document),
            )
            .where(ESignatureRequest.id == request_id, ESignatureRequest.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_request_id: str, tenant_id: UUID) -> ESignatureRequest | None:
        result = await self.db.execute(
            select(ESignatureRequest).where(
                ESignatureRequest.external_request_id == external_request_id,
                ESignatureRequest.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        document_id: UUID | None = None,
        engagement_document_id: UUID | None = None,
        provider: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[ESignatureRequest], int]:
        query = select(ESignatureRequest).where(ESignatureRequest.tenant_id == tenant_id)
        count_query = select(func.count(ESignatureRequest.id)).where(ESignatureRequest.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    ESignatureRequest.title.ilike(search_term),
                    ESignatureRequest.subject.ilike(search_term),
                    ESignatureRequest.external_request_id.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    ESignatureRequest.title.ilike(search_term),
                    ESignatureRequest.subject.ilike(search_term),
                    ESignatureRequest.external_request_id.ilike(search_term),
                )
            )

        if document_id:
            query = query.where(ESignatureRequest.document_id == document_id)
            count_query = count_query.where(ESignatureRequest.document_id == document_id)

        if engagement_document_id:
            query = query.where(ESignatureRequest.engagement_document_id == engagement_document_id)
            count_query = count_query.where(ESignatureRequest.engagement_document_id == engagement_document_id)

        if provider:
            query = query.where(ESignatureRequest.provider == provider)
            count_query = count_query.where(ESignatureRequest.provider == provider)

        if status:
            query = query.where(ESignatureRequest.status == status)
            count_query = count_query.where(ESignatureRequest.status == status)

        if date_from:
            query = query.where(ESignatureRequest.created_at >= date_from)
            count_query = count_query.where(ESignatureRequest.created_at >= date_from)

        if date_to:
            query = query.where(ESignatureRequest.created_at <= date_to)
            count_query = count_query.where(ESignatureRequest.created_at <= date_to)

        sort_column = getattr(ESignatureRequest, sort_by, ESignatureRequest.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(ESignatureRequest.document),
                selectinload(ESignatureRequest.engagement_document),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, request: ESignatureRequest) -> ESignatureRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def delete(self, request: ESignatureRequest) -> None:
        await self.db.delete(request)
        await self.db.flush()


class ESignerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, signer: ESigner) -> ESigner:
        self.db.add(signer)
        await self.db.flush()
        await self.db.refresh(signer)
        return signer

    async def get_by_id(self, signer_id: UUID, tenant_id: UUID) -> ESigner | None:
        result = await self.db.execute(
            select(ESigner)
            .options(
                selectinload(ESigner.request),
                selectinload(ESigner.signer),
            )
            .where(ESigner.id == signer_id, ESigner.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_signer_id: str, tenant_id: UUID) -> ESigner | None:
        result = await self.db.execute(
            select(ESigner).where(
                ESigner.external_signer_id == external_signer_id,
                ESigner.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_request(self, request_id: UUID, tenant_id: UUID) -> list[ESigner]:
        result = await self.db.execute(
            select(ESigner)
            .options(selectinload(ESigner.signer))
            .where(ESigner.request_id == request_id, ESigner.tenant_id == tenant_id)
            .order_by(ESigner.signing_order.asc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        request_id: UUID | None = None,
        signer_id: UUID | None = None,
        email: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[ESigner], int]:
        query = select(ESigner).where(ESigner.tenant_id == tenant_id)
        count_query = select(func.count(ESigner.id)).where(ESigner.tenant_id == tenant_id)

        if request_id:
            query = query.where(ESigner.request_id == request_id)
            count_query = count_query.where(ESigner.request_id == request_id)

        if signer_id:
            query = query.where(ESigner.signer_id == signer_id)
            count_query = count_query.where(ESigner.signer_id == signer_id)

        if email:
            query = query.where(ESigner.email.ilike(f"%{email}%"))
            count_query = count_query.where(ESigner.email.ilike(f"%{email}%"))

        if status:
            query = query.where(ESigner.status == status)
            count_query = count_query.where(ESigner.status == status)

        if date_from:
            query = query.where(ESigner.created_at >= date_from)
            count_query = count_query.where(ESigner.created_at >= date_from)

        if date_to:
            query = query.where(ESigner.created_at <= date_to)
            count_query = count_query.where(ESigner.created_at <= date_to)

        sort_column = getattr(ESigner, sort_by, ESigner.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(ESigner.request),
                selectinload(ESigner.signer),
            )
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, signer: ESigner) -> ESigner:
        await self.db.flush()
        await self.db.refresh(signer)
        return signer


class ESignatureProviderConfigRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, config: ESignatureProviderConfig) -> ESignatureProviderConfig:
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def get_by_id(self, config_id: UUID, tenant_id: UUID) -> ESignatureProviderConfig | None:
        result = await self.db.execute(
            select(ESignatureProviderConfig).where(
                ESignatureProviderConfig.id == config_id,
                ESignatureProviderConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_provider(self, provider: ESignatureProvider, tenant_id: UUID) -> ESignatureProviderConfig | None:
        result = await self.db.execute(
            select(ESignatureProviderConfig).where(
                ESignatureProviderConfig.provider == provider,
                ESignatureProviderConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_default(self, tenant_id: UUID) -> ESignatureProviderConfig | None:
        result = await self.db.execute(
            select(ESignatureProviderConfig).where(
                ESignatureProviderConfig.is_default == True,
                ESignatureProviderConfig.is_active == True,
                ESignatureProviderConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        provider: str | None = None,
        is_active: bool | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[ESignatureProviderConfig], int]:
        query = select(ESignatureProviderConfig).where(ESignatureProviderConfig.tenant_id == tenant_id)
        count_query = select(func.count(ESignatureProviderConfig.id)).where(ESignatureProviderConfig.tenant_id == tenant_id)

        if provider:
            query = query.where(ESignatureProviderConfig.provider == provider)
            count_query = count_query.where(ESignatureProviderConfig.provider == provider)

        if is_active is not None:
            query = query.where(ESignatureProviderConfig.is_active == is_active)
            count_query = count_query.where(ESignatureProviderConfig.is_active == is_active)

        sort_column = getattr(ESignatureProviderConfig, sort_by, ESignatureProviderConfig.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, config: ESignatureProviderConfig) -> ESignatureProviderConfig:
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def delete(self, config: ESignatureProviderConfig) -> None:
        await self.db.delete(config)
        await self.db.flush()


class ESignatureWebhookEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event: ESignatureWebhookEvent) -> ESignatureWebhookEvent:
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_by_id(self, event_id: UUID, tenant_id: UUID) -> ESignatureWebhookEvent | None:
        result = await self.db.execute(
            select(ESignatureWebhookEvent).where(
                ESignatureWebhookEvent.id == event_id,
                ESignatureWebhookEvent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str, tenant_id: UUID) -> ESignatureWebhookEvent | None:
        result = await self.db.execute(
            select(ESignatureWebhookEvent).where(
                ESignatureWebhookEvent.idempotency_key == idempotency_key,
                ESignatureWebhookEvent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_event_id: str, tenant_id: UUID) -> ESignatureWebhookEvent | None:
        result = await self.db.execute(
            select(ESignatureWebhookEvent).where(
                ESignatureWebhookEvent.external_event_id == external_event_id,
                ESignatureWebhookEvent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        provider: str | None = None,
        processed: bool | None = None,
        external_request_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[ESignatureWebhookEvent], int]:
        query = select(ESignatureWebhookEvent).where(ESignatureWebhookEvent.tenant_id == tenant_id)
        count_query = select(func.count(ESignatureWebhookEvent.id)).where(ESignatureWebhookEvent.tenant_id == tenant_id)

        if provider:
            query = query.where(ESignatureWebhookEvent.provider == provider)
            count_query = count_query.where(ESignatureWebhookEvent.provider == provider)

        if processed is not None:
            query = query.where(ESignatureWebhookEvent.processed == processed)
            count_query = count_query.where(ESignatureWebhookEvent.processed == processed)

        if external_request_id:
            query = query.where(ESignatureWebhookEvent.external_request_id == external_request_id)
            count_query = count_query.where(ESignatureWebhookEvent.external_request_id == external_request_id)

        if date_from:
            query = query.where(ESignatureWebhookEvent.received_at >= date_from)
            count_query = count_query.where(ESignatureWebhookEvent.received_at >= date_from)

        if date_to:
            query = query.where(ESignatureWebhookEvent.received_at <= date_to)
            count_query = count_query.where(ESignatureWebhookEvent.received_at <= date_to)

        sort_column = getattr(ESignatureWebhookEvent, sort_by, ESignatureWebhookEvent.received_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        total = await self.db.scalar(count_query)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def update(self, event: ESignatureWebhookEvent) -> ESignatureWebhookEvent:
        await self.db.flush()
        await self.db.refresh(event)
        return event