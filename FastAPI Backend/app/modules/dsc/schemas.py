from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DSCType(str, Enum):
    CLASS_1 = "class_1"
    CLASS_2 = "class_2"
    CLASS_3 = "class_3"
    DGFT = "dgft"


class DSCStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_RENEWAL = "pending_renewal"
    RENEWED = "renewed"


class DSCCertificateBase(BaseModel):
    holder_id: UUID
    dsc_type: DSCType
    certificate_serial_number: str = Field(..., min_length=1, max_length=200)
    issuing_authority: str = Field(..., min_length=1, max_length=200)
    issue_date: datetime
    expiry_date: datetime
    custodian_id: UUID | None = None
    client_id: UUID | None = None
    key_algorithm: str = Field(default="RSA", max_length=50)
    key_size: int = Field(default=2048, ge=1024, le=8192)
    token_serial_number: str | None = Field(None, max_length=100)
    token_type: str | None = Field(None, max_length=50)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class DSCCertificateCreate(DSCCertificateBase):
    pass


class DSCCertificateUpdate(BaseModel):
    dsc_type: DSCType | None = None
    status: str | None = None
    certificate_serial_number: str | None = Field(None, min_length=1, max_length=200)
    issuing_authority: str | None = Field(None, min_length=1, max_length=200)
    issue_date: datetime | None = None
    expiry_date: datetime | None = None
    custodian_id: UUID | None = None
    client_id: UUID | None = None
    key_algorithm: str | None = Field(None, max_length=50)
    key_size: int | None = Field(None, ge=1024, le=8192)
    token_serial_number: str | None = Field(None, max_length=100)
    token_type: str | None = Field(None, max_length=50)
    extra_metadata: dict[str, Any] | None = None


class DSCCertificateResponse(BaseModel):
    id: UUID
    holder_id: UUID
    dsc_type: DSCType
    status: str
    certificate_serial_number: str
    issuing_authority: str
    issue_date: datetime
    expiry_date: datetime
    custodian_id: UUID | None
    client_id: UUID | None
    key_algorithm: str
    key_size: int
    token_serial_number: str | None
    token_type: str | None
    renewal_reminder_sent: bool
    renewal_initiated_at: datetime | None
    revoked_at: datetime | None
    revoked_by: UUID | None
    revocation_reason: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class DSCCertificateDetailResponse(DSCCertificateResponse):
    holder: Any | None = None
    custodian: Any | None = None
    client: Any | None = None
    signing_logs_count: int = 0
    renewal_requests_count: int = 0


class DSCCertificateListResponse(BaseModel):
    items: list[DSCCertificateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DSCCertificateSignRequest(BaseModel):
    document_id: UUID | None = None
    signing_purpose: str = Field(..., min_length=1, max_length=200)
    signature_algorithm: str = Field(default="RSA-SHA256", max_length=100)
    pin: str | None = Field(None, min_length=4, max_length=20)


class DSCSigningLogBase(BaseModel):
    certificate_id: UUID
    document_id: UUID | None = None
    signing_purpose: str = Field(..., min_length=1, max_length=200)
    signature_algorithm: str = Field(default="RSA-SHA256", max_length=100)
    signature_hash: str = Field(..., min_length=1, max_length=200)
    status: str = Field(..., min_length=1, max_length=50)
    error_message: str | None = None
    ip_address: str | None = Field(None, max_length=50)
    user_agent: str | None = None
    request_id: str | None = Field(None, max_length=100)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class DSCSigningLogCreate(DSCSigningLogBase):
    pass


class DSCSigningLogResponse(BaseModel):
    id: UUID
    certificate_id: UUID
    document_id: UUID | None
    signed_by_id: UUID
    signing_purpose: str
    signature_algorithm: str
    signature_hash: str
    status: str
    error_message: str | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class DSCSigningLogListResponse(BaseModel):
    items: list[DSCSigningLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DSCRenewalRequestBase(BaseModel):
    certificate_id: UUID
    new_expiry_date: datetime | None = None
    renewal_authority: str | None = Field(None, max_length=200)
    renewal_reference: str | None = Field(None, max_length=200)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class DSCRenewalRequestCreate(DSCRenewalRequestBase):
    pass


class DSCRenewalRequestUpdate(BaseModel):
    status: str | None = None
    new_expiry_date: datetime | None = None
    renewal_authority: str | None = Field(None, max_length=200)
    renewal_reference: str | None = Field(None, max_length=200)
    approved_by_id: UUID | None = None
    approved_at: datetime | None = None
    rejected_by_id: UUID | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    extra_metadata: dict[str, Any] | None = None


class DSCRenewalRequestResponse(BaseModel):
    id: UUID
    certificate_id: UUID
    requested_by_id: UUID
    status: str
    new_expiry_date: datetime | None
    renewal_authority: str | None
    renewal_reference: str | None
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


class DSCRenewalRequestDetailResponse(DSCRenewalRequestResponse):
    certificate: Any | None = None
    requested_by: Any | None = None
    approved_by: Any | None = None
    rejected_by: Any | None = None


class DSCRenewalRequestListResponse(BaseModel):
    items: list[DSCRenewalRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DSCExpiringSoonResponse(BaseModel):
    certificate_id: UUID
    certificate_serial_number: str
    holder_name: str
    holder_email: str
    expiry_date: datetime
    days_until_expiry: int
    dsc_type: DSCType
    status: str