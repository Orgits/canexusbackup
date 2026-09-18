from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UDINStatus(str, Enum):
    GENERATED = "generated"
    VERIFIED = "verified"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class UDINRecordBase(BaseModel):
    professional_id: UUID
    financial_year: str = Field(..., min_length=1, max_length=20)
    quarter: str | None = Field(None, max_length=10)
    form_type: str | None = Field(None, max_length=50)
    client_id: UUID | None = None
    matter_id: UUID | None = None
    document_id: UUID | None = None
    description: str | None = None
    external_reference: str | None = Field(None, max_length=100)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class UDINRecordCreate(UDINRecordBase):
    pass


class UDINRecordUpdate(BaseModel):
    professional_id: UUID | None = None
    status: str | None = None
    financial_year: str | None = Field(None, min_length=1, max_length=20)
    quarter: str | None = Field(None, max_length=10)
    form_type: str | None = Field(None, max_length=50)
    client_id: UUID | None = None
    matter_id: UUID | None = None
    document_id: UUID | None = None
    description: str | None = None
    external_reference: str | None = Field(None, max_length=100)
    extra_metadata: dict[str, Any] | None = None


class UDINRecordResponse(BaseModel):
    id: UUID
    udin: str
    professional_id: UUID
    status: str
    client_id: UUID | None
    matter_id: UUID | None
    document_id: UUID | None
    financial_year: str
    quarter: str | None
    form_type: str | None
    description: str | None
    generated_at: datetime
    verified_at: datetime | None
    verified_by_id: UUID | None
    cancelled_at: datetime | None
    cancelled_by_id: UUID | None
    cancellation_reason: str | None
    external_reference: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class UDINRecordDetailResponse(UDINRecordResponse):
    professional: Any | None = None
    client: Any | None = None
    matter: Any | None = None
    document: Any | None = None
    verified_by: Any | None = None
    cancelled_by: Any | None = None
    verification_logs_count: int = 0


class UDINRecordListResponse(BaseModel):
    items: list[UDINRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UDINGenerationRequest(BaseModel):
    professional_id: UUID
    financial_year: str = Field(..., min_length=1, max_length=20)
    quarter: str | None = Field(None, max_length=10)
    form_type: str | None = Field(None, max_length=50)
    client_id: UUID | None = None
    matter_id: UUID | None = None
    document_id: UUID | None = None
    description: str | None = None
    external_reference: str | None = Field(None, max_length=100)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class UDINGenerationResponse(BaseModel):
    udin: str
    generated_at: datetime
    record_id: UUID


class UDINVerificationRequest(BaseModel):
    udin: str = Field(..., min_length=18, max_length=20)
    verification_method: str = Field(default="manual", max_length=50)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class UDINVerificationResponse(BaseModel):
    udin: str
    status: str
    verified: bool
    verified_at: datetime | None
    professional_name: str | None
    client_name: str | None
    matter_name: str | None
    document_name: str | None
    financial_year: str
    form_type: str | None
    external_response: dict | None = None


class UDINVerificationLogBase(BaseModel):
    udin_record_id: UUID
    result: str = Field(..., min_length=1, max_length=50)
    verification_method: str = Field(..., min_length=1, max_length=50)
    external_response: dict[str, Any] | None = None
    ip_address: str | None = Field(None, max_length=50)
    user_agent: str | None = None
    request_id: str | None = Field(None, max_length=100)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class UDINVerificationLogCreate(UDINVerificationLogBase):
    pass


class UDINVerificationLogResponse(BaseModel):
    id: UUID
    udin_record_id: UUID
    verified_by_id: UUID
    result: str
    verification_method: str
    external_response: dict[str, Any] | None
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


class UDINVerificationLogListResponse(BaseModel):
    items: list[UDINVerificationLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int