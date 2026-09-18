from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EngagementDocumentType(str, Enum):
    ENGAGEMENT_LETTER = "engagement_letter"
    REPRESENTATION_LETTER = "representation_letter"
    MANAGEMENT_LETTER = "management_letter"
    CONFIRMATION_LETTER = "confirmation_letter"
    INDEPENDENCE_DECLARATION = "independence_declaration"
    TERMS_OF_BUSINESS = "terms_of_business"
    SCOPE_OF_WORK = "scope_of_work"
    FEE_AGREEMENT = "fee_agreement"
    NDA = "nda"
    OTHER = "other"


class EngagementDocumentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_SIGNATURE = "pending_signature"
    PARTIALLY_SIGNED = "partially_signed"
    FULLY_SIGNED = "fully_signed"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EngagementDocumentBase(BaseModel):
    client_id: UUID
    matter_id: UUID | None = None
    document_type: EngagementDocumentType
    document_number: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    template_id: UUID | None = None
    template_version: int | None = None
    engagement_partner_id: UUID | None = None
    engagement_manager_id: UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    fee_estimate: float | None = None
    fee_terms: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class EngagementDocumentCreate(EngagementDocumentBase):
    pass


class EngagementDocumentUpdate(BaseModel):
    client_id: UUID | None = None
    matter_id: UUID | None = None
    document_type: EngagementDocumentType | None = None
    status: str | None = None
    document_number: str | None = Field(None, min_length=1, max_length=100)
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    template_id: UUID | None = None
    template_version: int | None = None
    engagement_partner_id: UUID | None = None
    engagement_manager_id: UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    fee_estimate: float | None = None
    fee_terms: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    variables: dict[str, Any] | None = None
    extra_metadata: dict[str, Any] | None = None


class EngagementDocumentResponse(BaseModel):
    id: UUID
    client_id: UUID
    matter_id: UUID | None
    document_type: EngagementDocumentType
    status: str
    document_number: str
    title: str
    description: str | None
    template_id: UUID | None
    template_version: int | None
    engagement_partner_id: UUID | None
    engagement_manager_id: UUID | None
    period_start: datetime | None
    period_end: datetime | None
    fee_estimate: float | None
    fee_terms: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    variables: dict[str, Any]
    signed_at: datetime | None
    completed_at: datetime | None
    e_signature_request_id: UUID | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class EngagementDocumentDetailResponse(EngagementDocumentResponse):
    client: Any | None = None
    matter: Any | None = None
    engagement_partner: Any | None = None
    engagement_manager: Any | None = None
    signers: list[Any] = Field(default_factory=list)
    versions_count: int = 0


class EngagementDocumentListResponse(BaseModel):
    items: list[EngagementDocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EngagementDocumentSignerBase(BaseModel):
    engagement_document_id: UUID
    signer_id: UUID
    signer_role: str = Field(..., min_length=1, max_length=100)
    signing_order: int = Field(default=1, ge=1)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class EngagementDocumentSignerCreate(EngagementDocumentSignerBase):
    pass


class EngagementDocumentSignerUpdate(BaseModel):
    signer_id: UUID | None = None
    signer_role: str | None = Field(None, min_length=1, max_length=100)
    signing_order: int | None = Field(None, ge=1)
    status: str | None = None
    signature_data: dict[str, Any] | None = None
    decline_reason: str | None = None
    extra_metadata: dict[str, Any] | None = None


class EngagementDocumentSignerResponse(BaseModel):
    id: UUID
    engagement_document_id: UUID
    signer_id: UUID
    signer_role: str
    signing_order: int
    status: str
    signed_at: datetime | None
    signature_data: dict[str, Any] | None
    declined_at: datetime | None
    decline_reason: str | None
    reminder_sent_at: datetime | None
    reminder_count: int
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class EngagementDocumentSignerDetailResponse(EngagementDocumentSignerResponse):
    signer: Any | None = None


class EngagementDocumentVersionBase(BaseModel):
    engagement_document_id: UUID
    version: int = Field(..., ge=1)
    document_content: str | None = None
    document_html: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    change_summary: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class EngagementDocumentVersionCreate(EngagementDocumentVersionBase):
    pass


class EngagementDocumentVersionResponse(BaseModel):
    id: UUID
    engagement_document_id: UUID
    version: int
    document_content: str | None
    document_html: str | None
    variables: dict[str, Any]
    created_by_id: UUID
    change_summary: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class EngagementDocumentVersionDetailResponse(EngagementDocumentVersionResponse):
    created_by: Any | None = None


class EngagementDocumentTemplateBase(BaseModel):
    document_type: EngagementDocumentType
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    content_template: str = Field(..., min_length=1)
    html_template: str | None = None
    default_variables: dict[str, Any] = Field(default_factory=dict)
    required_variables: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_default: bool = False
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class EngagementDocumentTemplateCreate(EngagementDocumentTemplateBase):
    pass


class EngagementDocumentTemplateUpdate(BaseModel):
    document_type: EngagementDocumentType | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    content_template: str | None = None
    html_template: str | None = None
    default_variables: dict[str, Any] | None = None
    required_variables: list[str] | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    version: int | None = Field(None, ge=1)
    extra_metadata: dict[str, Any] | None = None


class EngagementDocumentTemplateResponse(BaseModel):
    id: UUID
    document_type: EngagementDocumentType
    name: str
    description: str | None
    content_template: str
    html_template: str | None
    default_variables: dict[str, Any]
    required_variables: list[str]
    is_active: bool
    is_default: bool
    version: int
    created_by_id: UUID
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class EngagementDocumentTemplateDetailResponse(EngagementDocumentTemplateResponse):
    created_by: Any | None = None


class EngagementDocumentTemplateListResponse(BaseModel):
    items: list[EngagementDocumentTemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int