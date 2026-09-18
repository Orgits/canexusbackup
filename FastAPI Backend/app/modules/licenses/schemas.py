from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LicenseType(str, Enum):
    CA_CERTIFICATE = "ca_certificate"
    CA_PRACTICE_CERTIFICATE = "ca_practice_certificate"
    GST_PRACTITIONER = "gst_practitioner"
    TAX_AUDITOR = "tax_auditor"
    COMPANY_SECRETARY = "company_secretary"
    COST_ACCOUNTANT = "cost_accountant"
    INSOLVENCY_PROFESSIONAL = "insolvency_professional"
    REGISTERED_VALUER = "registered_valuer"
    PEER_REVIEW_CERTIFICATE = "peer_review_certificate"
    QUALITY_REVIEW_CERTIFICATE = "quality_review_certificate"
    FCRA_REGISTRATION = "fcra_registration"
    INCOME_TAX_PRACTITIONER = "income_tax_practitioner"
    OTHER = "other"


class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING_RENEWAL = "pending_renewal"
    RENEWED = "renewed"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    SURRENDERED = "surrendered"


class LicenseBase(BaseModel):
    professional_id: UUID
    license_type: LicenseType
    license_number: str = Field(..., min_length=1, max_length=100)
    issuing_authority: str = Field(..., min_length=1, max_length=200)
    issue_date: datetime
    expiry_date: datetime
    registration_number: str | None = Field(None, max_length=100)
    jurisdiction: str | None = Field(None, max_length=100)
    scope: str | None = None
    conditions: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class LicenseCreate(LicenseBase):
    pass


class LicenseUpdate(BaseModel):
    professional_id: UUID | None = None
    license_type: LicenseType | None = None
    status: str | None = None
    license_number: str | None = Field(None, min_length=1, max_length=100)
    issuing_authority: str | None = Field(None, min_length=1, max_length=200)
    issue_date: datetime | None = None
    expiry_date: datetime | None = None
    registration_number: str | None = Field(None, max_length=100)
    jurisdiction: str | None = Field(None, max_length=100)
    scope: str | None = None
    conditions: str | None = None
    extra_metadata: dict[str, Any] | None = None


class LicenseResponse(BaseModel):
    id: UUID
    professional_id: UUID
    license_type: LicenseType
    status: str
    license_number: str
    issuing_authority: str
    issue_date: datetime
    expiry_date: datetime
    registration_number: str | None
    jurisdiction: str | None
    scope: str | None
    conditions: str | None
    renewal_application_date: datetime | None
    renewal_acknowledgment_number: str | None
    renewed_at: datetime | None
    renewed_by_id: UUID | None
    suspended_at: datetime | None
    suspended_by_id: UUID | None
    suspension_reason: str | None
    revoked_at: datetime | None
    revoked_by_id: UUID | None
    revocation_reason: str | None
    reminder_sent_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class LicenseDetailResponse(LicenseResponse):
    professional: Any | None = None
    renewed_by: Any | None = None
    suspended_by: Any | None = None
    revoked_by: Any | None = None
    documents_count: int = 0
    renewal_requests_count: int = 0


class LicenseListResponse(BaseModel):
    items: list[LicenseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LicenseExpiringSoonResponse(BaseModel):
    license_id: UUID
    license_number: str
    professional_name: str
    professional_email: str
    expiry_date: datetime
    days_until_expiry: int
    license_type: LicenseType
    status: str


class LicenseDocumentCreate(BaseModel):
    license_id: UUID
    document_id: UUID
    document_type: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class LicenseDocumentResponse(BaseModel):
    id: UUID
    license_id: UUID
    document_id: UUID
    document_type: str
    description: str | None
    uploaded_by_id: UUID
    uploaded_at: datetime
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class LicenseDocumentListResponse(BaseModel):
    items: list[LicenseDocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LicenseRenewalRequestCreate(BaseModel):
    license_id: UUID
    new_expiry_date: datetime | None = None
    application_number: str | None = Field(None, max_length=100)
    application_date: datetime | None = None
    fees_amount: float | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class LicenseRenewalRequestUpdate(BaseModel):
    status: str | None = None
    new_expiry_date: datetime | None = None
    application_number: str | None = Field(None, max_length=100)
    application_date: datetime | None = None
    fees_paid: bool | None = None
    fees_amount: float | None = None
    fees_paid_at: datetime | None = None
    approved_by_id: UUID | None = None
    approved_at: datetime | None = None
    rejected_by_id: UUID | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    extra_metadata: dict[str, Any] | None = None


class LicenseRenewalRequestResponse(BaseModel):
    id: UUID
    license_id: UUID
    requested_by_id: UUID
    status: str
    new_expiry_date: datetime | None
    application_number: str | None
    application_date: datetime | None
    fees_paid: bool
    fees_amount: float | None
    fees_paid_at: datetime | None
    approved_by_id: UUID | None
    approved_at: datetime | None
    rejected_by_id: UUID | None
    rejected_at: datetime | None
    rejection_reason: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class LicenseRenewalRequestDetailResponse(LicenseRenewalRequestResponse):
    license: Any | None = None
    requested_by: Any | None = None
    approved_by: Any | None = None
    rejected_by: Any | None = None


class LicenseRenewalRequestListResponse(BaseModel):
    items: list[LicenseRenewalRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int