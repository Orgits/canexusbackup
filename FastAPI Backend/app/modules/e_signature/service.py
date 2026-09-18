import hmac
import hashlib
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.security.encryption import encrypt_field, decrypt_field
from app.modules.e_signature.models import (
    ESignatureRequest,
    ESigner,
    ESignatureProviderConfig,
    ESignatureWebhookEvent,
    ESignatureRequestStatus,
    ESignerStatus,
    ESignatureProvider,
)
from app.modules.e_signature.repository import (
    ESignatureRequestRepository,
    ESignerRepository,
    ESignatureProviderConfigRepository,
    ESignatureWebhookEventRepository,
)
from app.modules.e_signature.schemas import (
    ESignatureRequestCreate,
    ESignatureRequestUpdate,
    ESignatureSendRequest,
    ESignatureCancelRequest,
    ESignerCreate,
    ESignerUpdate,
    ESignatureProviderConfigCreate,
    ESignatureProviderConfigUpdate,
    ESignatureWebhookEventCreate,
)
from app.modules.users.models import User
from app.modules.documents.models import Document
from app.modules.engagement_documents.models import EngagementDocument


class ESignatureProviderService:
    """Base class for e-signature provider integrations"""

    @staticmethod
    async def send_request(request: ESignatureRequest, config: ESignatureProviderConfig) -> dict:
        """Send signature request to provider - to be implemented per provider"""
        raise NotImplementedError("Provider-specific implementation required")

    @staticmethod
    async def cancel_request(request: ESignatureRequest, config: ESignatureProviderConfig) -> dict:
        """Cancel signature request with provider - to be implemented per provider"""
        raise NotImplementedError("Provider-specific implementation required")

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def parse_webhook_event(provider: ESignatureProvider, payload: dict) -> dict:
        """Parse provider-specific webhook payload to standard format - to be implemented per provider"""
        raise NotImplementedError("Provider-specific implementation required")


class DocuSignProviderService(ESignatureProviderService):
    """DocuSign-specific implementation"""

    @staticmethod
    async def send_request(request: ESignatureRequest, config: ESignatureProviderConfig) -> dict:
        # Placeholder for DocuSign API integration
        # In production, this would call DocuSign REST API
        return {
            "external_request_id": f"docusign_{request.id}",
            "status": "sent",
        }

    @staticmethod
    async def cancel_request(request: ESignatureRequest, config: ESignatureProviderConfig) -> dict:
        return {"status": "cancelled"}

    @staticmethod
    def parse_webhook_event(provider: ESignatureProvider, payload: dict) -> dict:
        # Parse DocuSign Connect webhook format
        return {
            "external_event_id": payload.get("eventId", ""),
            "event_type": payload.get("event", ""),
            "external_request_id": payload.get("envelopeId", ""),
        }


class AdobeSignProviderService(ESignatureProviderService):
    """Adobe Sign-specific implementation"""

    @staticmethod
    async def send_request(request: ESignatureRequest, config: ESignatureProviderConfig) -> dict:
        # Placeholder for Adobe Sign API integration
        return {
            "external_request_id": f"adobe_{request.id}",
            "status": "sent",
        }

    @staticmethod
    async def cancel_request(request: ESignatureRequest, config: ESignatureProviderConfig) -> dict:
        return {"status": "cancelled"}

    @staticmethod
    def parse_webhook_event(provider: ESignatureProvider, payload: dict) -> dict:
        return {
            "external_event_id": payload.get("id", ""),
            "event_type": payload.get("type", ""),
            "external_request_id": payload.get("agreementId", ""),
        }


class ESignatureRequestService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.request_repo = ESignatureRequestRepository(db)
        self.signer_repo = ESignerRepository(db)
        self.provider_config_repo = ESignatureProviderConfigRepository(db)

    def _get_provider_service(self, provider: ESignatureProvider) -> ESignatureProviderService:
        services = {
            ESignatureProvider.DOCUSIGN: DocuSignProviderService,
            ESignatureProvider.ADOBE_SIGN: AdobeSignProviderService,
        }
        return services.get(provider, ESignatureProviderService)()

    async def create(self, data: ESignatureRequestCreate, tenant_id: UUID, created_by: UUID) -> ESignatureRequest:
        # Validate document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == data.document_id, Document.tenant_id == tenant_id)
        )
        if not doc_result.scalar_one_or_none():
            raise NotFoundException(detail="Document not found")

        # Validate engagement document if provided
        if data.engagement_document_id:
            eng_doc_result = await self.db.execute(
                select(EngagementDocument).where(
                    EngagementDocument.id == data.engagement_document_id,
                    EngagementDocument.tenant_id == tenant_id,
                )
            )
            if not eng_doc_result.scalar_one_or_none():
                raise NotFoundException(detail="Engagement document not found")

        # Validate provider config exists
        provider_config = await self.provider_config_repo.get_by_provider(data.provider, tenant_id)
        if not provider_config:
            raise ValidationException(detail=f"No active configuration for provider {data.provider.value}")

        request = ESignatureRequest(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=ESignatureRequestStatus.DRAFT.value,
        )
        return await self.request_repo.create(request)

    async def get_by_id(self, request_id: UUID, tenant_id: UUID) -> ESignatureRequest:
        request = await self.request_repo.get_by_id(request_id, tenant_id)
        if not request:
            raise NotFoundException(detail="E-Signature request not found")
        return request

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
        return await self.request_repo.get_all(
            tenant_id, page, page_size, search, document_id, engagement_document_id,
            provider, status, date_from, date_to, sort_by, sort_order
        )

    async def update(self, request_id: UUID, tenant_id: UUID, data: ESignatureRequestUpdate, updated_by: UUID) -> ESignatureRequest:
        request = await self.get_by_id(request_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            valid_transitions = {
                ESignatureRequestStatus.DRAFT.value: [ESignatureRequestStatus.PENDING.value, ESignatureRequestStatus.CANCELLED.value],
                ESignatureRequestStatus.PENDING.value: [ESignatureRequestStatus.SENT.value, ESignatureRequestStatus.CANCELLED.value, ESignatureRequestStatus.FAILED.value],
                ESignatureRequestStatus.SENT.value: [ESignatureRequestStatus.IN_PROGRESS.value, ESignatureRequestStatus.COMPLETED.value, ESignatureRequestStatus.DECLINED.value, ESignatureRequestStatus.EXPIRED.value, ESignatureRequestStatus.CANCELLED.value],
                ESignatureRequestStatus.IN_PROGRESS.value: [ESignatureRequestStatus.COMPLETED.value, ESignatureRequestStatus.DECLINED.value, ESignatureRequestStatus.EXPIRED.value, ESignatureRequestStatus.CANCELLED.value],
                ESignatureRequestStatus.COMPLETED.value: [],
                ESignatureRequestStatus.DECLINED.value: [],
                ESignatureRequestStatus.EXPIRED.value: [],
                ESignatureRequestStatus.CANCELLED.value: [],
                ESignatureRequestStatus.FAILED.value: [ESignatureRequestStatus.PENDING.value],
            }
            current_status = request.status
            if new_status not in valid_transitions.get(current_status, []):
                raise ValidationException(detail=f"Invalid status transition from {current_status} to {new_status}")

            if new_status == ESignatureRequestStatus.COMPLETED.value:
                request.completed_at = datetime.utcnow()
            elif new_status == ESignatureRequestStatus.DECLINED.value:
                request.declined_at = datetime.utcnow()
                request.declined_by_id = updated_by
                if "decline_reason" in update_data:
                    request.decline_reason = update_data.pop("decline_reason")

        for field, value in update_data.items():
            setattr(request, field, value)

        request.updated_by = updated_by
        return await self.request_repo.update(request)

    async def send(self, data: ESignatureSendRequest, tenant_id: UUID, sent_by: UUID) -> ESignatureRequest:
        request = await self.get_by_id(data.request_id, tenant_id)

        if request.status not in [ESignatureRequestStatus.DRAFT.value, ESignatureRequestStatus.PENDING.value]:
            raise ValidationException(detail=f"Cannot send request with status: {request.status}")

        # Get provider config
        provider_config = await self.provider_config_repo.get_by_provider(request.provider, tenant_id)
        if not provider_config:
            raise ValidationException(detail=f"No active configuration for provider {request.provider.value}")

        # Create signers if provided
        if data.signers:
            for signer_data in data.signers:
                signer = ESigner(
                    request_id=request.id,
                    signer_id=signer_data.signer_id,
                    email=signer_data.email,
                    name=signer_data.name,
                    role=signer_data.role,
                    signing_order=signer_data.signing_order,
                    authentication_method=signer_data.authentication_method,
                    access_code=signer_data.access_code,
                    phone_number=signer_data.phone_number,
                    status=ESignerStatus.PENDING.value,
                    tenant_id=tenant_id,
                    created_by=sent_by,
                    extra_metadata=signer_data.extra_metadata,
                )
                await self.signer_repo.create(signer)

        # Check idempotency
        if data.idempotency_key:
            existing_webhook = await self.db.execute(
                select(ESignatureWebhookEvent).where(
                    ESignatureWebhookEvent.idempotency_key == data.idempotency_key,
                    ESignatureWebhookEvent.tenant_id == tenant_id,
                )
            )
            if existing_webhook.scalar_one_or_none():
                raise ValidationException(detail="Request with this idempotency key already processed")

        # Send to provider
        provider_service = self._get_provider_service(request.provider)
        try:
            provider_response = await provider_service.send_request(request, provider_config)
            request.external_request_id = provider_response.get("external_request_id")
            request.provider_response = provider_response
            request.status = ESignatureRequestStatus.SENT.value
            request.updated_by = sent_by
        except Exception as e:
            request.status = ESignatureRequestStatus.FAILED.value
            request.provider_response = {"error": str(e)}
            request.updated_by = sent_by
            await self.request_repo.update(request)
            raise ValidationException(detail=f"Failed to send to provider: {str(e)}")

        return await self.request_repo.update(request)

    async def cancel(self, data: ESignatureCancelRequest, tenant_id: UUID, cancelled_by: UUID) -> ESignatureRequest:
        request = await self.get_by_id(data.request_id, tenant_id)

        if request.status in [ESignatureRequestStatus.COMPLETED.value, ESignatureRequestStatus.CANCELLED.value]:
            raise ValidationException(detail=f"Cannot cancel request with status: {request.status}")

        # Cancel with provider if already sent
        if request.external_request_id:
            provider_config = await self.provider_config_repo.get_by_provider(request.provider, tenant_id)
            if provider_config:
                provider_service = self._get_provider_service(request.provider)
                try:
                    await provider_service.cancel_request(request, provider_config)
                except Exception as e:
                    # Log error but continue with local cancellation
                    pass

        request.status = ESignatureRequestStatus.CANCELLED.value
        request.declined_at = datetime.utcnow()
        request.declined_by_id = cancelled_by
        request.decline_reason = data.reason
        request.updated_by = cancelled_by
        return await self.request_repo.update(request)

    async def send_reminders(self, tenant_id: UUID) -> int:
        """Send reminders for pending requests - called by background worker"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=1)  # Default 1 day
        
        # Find requests that need reminders
        result = await self.db.execute(
            select(ESignatureRequest).where(
                ESignatureRequest.tenant_id == tenant_id,
                ESignatureRequest.status.in_([ESignatureRequestStatus.SENT.value, ESignatureRequestStatus.IN_PROGRESS.value]),
                ESignatureRequest.expires_at > datetime.utcnow(),
            )
        )
        requests = list(result.scalars().all())
        
        sent_count = 0
        for request in requests:
            if request.reminder_frequency_days:
                last_reminder = request.last_reminder_sent_at or request.created_at
                if (datetime.utcnow() - last_reminder).days >= request.reminder_frequency_days:
                    # Send reminder via provider
                    # This would call provider-specific reminder API
                    request.reminder_count += 1
                    request.last_reminder_sent_at = datetime.utcnow()
                    request.updated_by = None  # System
                    await self.request_repo.update(request)
                    sent_count += 1
        
        return sent_count

    async def delete(self, request_id: UUID, tenant_id: UUID) -> None:
        request = await self.get_by_id(request_id, tenant_id)
        await self.request_repo.delete(request)


class ESignerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.request_repo = ESignatureRequestRepository(db)
        self.signer_repo = ESignerRepository(db)

    async def get_signers(self, request_id: UUID, tenant_id: UUID) -> list[ESigner]:
        return await self.signer_repo.get_by_request(request_id, tenant_id)

    async def update_signer(self, signer_id: UUID, tenant_id: UUID, data: ESignerUpdate, updated_by: UUID) -> ESigner:
        signer = await self.signer_repo.get_by_id(signer_id, tenant_id)
        if not signer:
            raise NotFoundException(detail="Signer not found")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(signer, field, value)

        signer.updated_by = updated_by
        return await self.signer_repo.update(signer)

    async def handle_provider_callback(self, signer_id: UUID, tenant_id: UUID, event_data: dict) -> ESigner:
        signer = await self.signer_repo.get_by_id(signer_id, tenant_id)
        if not signer:
            raise NotFoundException(detail="Signer not found")

        # Update signer status based on provider event
        event_type = event_data.get("event_type", "").lower()
        if event_type in ["viewed", "opened"]:
            signer.status = ESignerStatus.VIEWED.value
            signer.viewed_at = datetime.utcnow()
        elif event_type in ["signed", "completed"]:
            signer.status = ESignerStatus.SIGNED.value
            signer.signed_at = datetime.utcnow()
            signer.signature_data = event_data.get("signature_data")
        elif event_type in ["declined", "rejected"]:
            signer.status = ESignerStatus.DECLINED.value
            signer.declined_at = datetime.utcnow()
            signer.decline_reason = event_data.get("decline_reason")
        elif event_type in ["expired"]:
            signer.status = ESignerStatus.EXPIRED.value

        signer.provider_response = event_data
        signer.updated_by = None  # System
        return await self.signer_repo.update(signer)


class ESignatureProviderConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider_config_repo = ESignatureProviderConfigRepository(db)

    async def create(self, data: ESignatureProviderConfigCreate, tenant_id: UUID, created_by: UUID) -> ESignatureProviderConfig:
        # If setting as default, unset other defaults
        if data.is_default:
            existing_default = await self.provider_config_repo.get_default(tenant_id)
            if existing_default:
                existing_default.is_default = False
                await self.provider_config_repo.update(existing_default)

        # Encrypt secrets
        client_secret_encrypted = encrypt_field(data.client_secret.encode())
        webhook_secret_encrypted = encrypt_field(data.webhook_secret.encode()) if data.webhook_secret else None

        config = ESignatureProviderConfig(
            provider=data.provider,
            is_active=data.is_active,
            is_default=data.is_default,
            api_base_url=data.api_base_url,
            client_id=data.client_id,
            client_secret_encrypted=client_secret_encrypted,
            account_id=data.account_id,
            webhook_secret_encrypted=webhook_secret_encrypted,
            oauth_redirect_uri=data.oauth_redirect_uri,
            scopes=data.scopes,
            rate_limit_per_minute=data.rate_limit_per_minute,
            timeout_seconds=data.timeout_seconds,
            extra_config=data.extra_config,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.provider_config_repo.create(config)

    async def get_by_id(self, config_id: UUID, tenant_id: UUID) -> ESignatureProviderConfig:
        config = await self.provider_config_repo.get_by_id(config_id, tenant_id)
        if not config:
            raise NotFoundException(detail="Provider configuration not found")
        return config

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
        return await self.provider_config_repo.get_all(
            tenant_id, page, page_size, provider, is_active, sort_by, sort_order
        )

    async def get_default(self, tenant_id: UUID) -> ESignatureProviderConfig | None:
        return await self.provider_config_repo.get_default(tenant_id)

    async def update(self, config_id: UUID, tenant_id: UUID, data: ESignatureProviderConfigUpdate, updated_by: UUID) -> ESignatureProviderConfig:
        config = await self.get_by_id(config_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle default flag
        if "is_default" in update_data and update_data["is_default"]:
            existing_default = await self.provider_config_repo.get_default(tenant_id)
            if existing_default and existing_default.id != config_id:
                existing_default.is_default = False
                await self.provider_config_repo.update(existing_default)

        # Encrypt secrets if provided
        if "client_secret" in update_data and update_data["client_secret"]:
            config.client_secret_encrypted = encrypt_field(update_data.pop("client_secret").encode())
        if "webhook_secret" in update_data and update_data["webhook_secret"]:
            config.webhook_secret_encrypted = encrypt_field(update_data.pop("webhook_secret").encode())

        for field, value in update_data.items():
            setattr(config, field, value)

        config.updated_by = updated_by
        return await self.provider_config_repo.update(config)

    async def get_decrypted_secret(self, config_id: UUID, tenant_id: UUID) -> tuple[str, str | None]:
        """Get decrypted client secret and webhook secret for API calls"""
        config = await self.get_by_id(config_id, tenant_id)
        client_secret = decrypt_field(config.client_secret_encrypted).decode()
        webhook_secret = None
        if config.webhook_secret_encrypted:
            webhook_secret = decrypt_field(config.webhook_secret_encrypted).decode()
        return client_secret, webhook_secret


class ESignatureWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.request_repo = ESignatureRequestRepository(db)
        self.signer_repo = ESignerRepository(db)
        self.webhook_repo = ESignatureWebhookEventRepository(db)
        self.provider_config_repo = ESignatureProviderConfigRepository(db)

    async def process_webhook(self, data: ESignatureWebhookEventCreate, tenant_id: UUID) -> ESignatureWebhookEvent:
        # Check idempotency
        if data.idempotency_key:
            existing = await self.webhook_repo.get_by_idempotency_key(data.idempotency_key, tenant_id)
            if existing:
                return existing

        # Verify signature if webhook secret configured
        provider_config = await self.provider_config_repo.get_by_provider(data.provider, tenant_id)
        if provider_config and provider_config.webhook_secret_encrypted:
            webhook_secret = decrypt_field(provider_config.webhook_secret_encrypted).decode()
            # In production, verify signature from request headers
            # For now, we skip actual verification in this service

        # Create webhook event record
        event = ESignatureWebhookEvent(
            provider=data.provider,
            external_event_id=data.external_event_id,
            event_type=data.event_type,
            external_request_id=data.external_request_id,
            payload=data.payload,
            idempotency_key=data.idempotency_key,
            received_at=datetime.utcnow(),
            tenant_id=tenant_id,
            created_by=None,  # System
        )
        await self.webhook_repo.create(event)

        # Process event
        try:
            if data.external_request_id:
                request = await self.request_repo.get_by_external_id(data.external_request_id, tenant_id)
                if request:
                    await self._process_request_event(request, event, data.payload)
            
            event.processed = True
            event.processed_at = datetime.utcnow()
            await self.webhook_repo.update(event)
        except Exception as e:
            event.processing_error = str(e)
            event.retry_count += 1
            await self.webhook_repo.update(event)

        return event

    async def _process_request_event(self, request: ESignatureRequest, event: ESignatureWebhookEvent, payload: dict) -> None:
        provider_service = self._get_provider_service(request.provider)
        parsed = provider_service.parse_webhook_event(request.provider, payload)
        
        # Update request status based on event
        event_type = parsed.get("event_type", "").lower()
        if event_type in ["completed", "signed"]:
            request.status = ESignatureRequestStatus.COMPLETED.value
            request.completed_at = datetime.utcnow()
        elif event_type in ["declined", "rejected"]:
            request.status = ESignatureRequestStatus.DECLINED.value
            request.declined_at = datetime.utcnow()
        elif event_type in ["expired"]:
            request.status = ESignatureRequestStatus.EXPIRED.value
        elif event_type in ["cancelled", "voided"]:
            request.status = ESignatureRequestStatus.CANCELLED.value

        request.webhook_events.append(payload)
        request.updated_by = None
        await self.request_repo.update(request)

        # Update signers
        for signer in request.signers:
            if signer.external_signer_id:
                await self._process_signer_event(signer, event, payload)

    async def _process_signer_event(self, signer: ESigner, event: ESignatureWebhookEvent, payload: dict) -> None:
        # In production, match signer by external_signer_id from payload
        # For now, we update based on general event
        event_type = payload.get("event", "").lower()
        if event_type in ["viewed", "opened"]:
            signer.status = ESignerStatus.VIEWED.value
            signer.viewed_at = datetime.utcnow()
        elif event_type in ["signed", "completed"]:
            signer.status = ESignerStatus.SIGNED.value
            signer.signed_at = datetime.utcnow()
        elif event_type in ["declined", "rejected"]:
            signer.status = ESignerStatus.DECLINED.value
            signer.declined_at = datetime.utcnow()

        signer.provider_response = payload
        signer.updated_by = None
        await self.signer_repo.update(signer)

    def _get_provider_service(self, provider: ESignatureProvider) -> ESignatureProviderService:
        services = {
            ESignatureProvider.DOCUSIGN: DocuSignProviderService,
            ESignatureProvider.ADOBE_SIGN: AdobeSignProviderService,
        }
        return services.get(provider, ESignatureProviderService)()

    async def get_webhook_events(
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
        return await self.webhook_repo.get_all(
            tenant_id, page, page_size, provider, processed, external_request_id,
            date_from, date_to, sort_by, sort_order
        )