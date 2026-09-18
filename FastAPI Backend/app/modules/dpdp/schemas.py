from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.modules.dpdp.models import (
    DataAccessStatus,
    DataCorrectionStatus,
    DataErasureStatus,
    RetentionAction,
)


class DataAccessRequestBase(BaseModel):
    subject_id: UUID
    client_id: Optional[UUID] = None
    scope: dict = Field(default_factory=dict)
    legal_basis: Optional[str] = Field(None, max_length=255)


class DataAccessRequestCreate(DataAccessRequestBase):
    pass


class DataAccessRequestUpdate(BaseModel):
    status: Optional[DataAccessStatus] = None
    rejection_reason: Optional[str] = None
    compiled_data_ref: Optional[str] = Field(None, max_length=500)
    compiled_size: Optional[int] = None
    compiled_checksum: Optional[str] = Field(None, max_length=64)
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DataAccessRequestResponse(DataAccessRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DataAccessStatus
    compiled_data_ref: Optional[str] = None
    compiled_size: Optional[int] = None
    compiled_checksum: Optional[str] = None
    approved_by_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    delivered_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DataAccessRequestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_id: UUID
    client_id: Optional[UUID] = None
    status: DataAccessStatus
    approved_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DataCorrectionRequestBase(BaseModel):
    subject_id: UUID
    client_id: Optional[UUID] = None
    entity_type: str = Field(..., max_length=100)
    entity_id: UUID
    field_name: str = Field(..., max_length=100)
    old_value: Optional[str] = None
    new_value: str
    justification: str


class DataCorrectionRequestCreate(DataCorrectionRequestBase):
    pass


class DataCorrectionRequestUpdate(BaseModel):
    status: Optional[DataCorrectionStatus] = None
    review_notes: Optional[str] = None
    error_message: Optional[str] = None


class DataCorrectionRequestResponse(DataCorrectionRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DataCorrectionStatus
    reviewed_by_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    applied_by_id: Optional[UUID] = None
    error_message: Optional[str] = None
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DataCorrectionRequestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_id: UUID
    client_id: Optional[UUID] = None
    entity_type: str
    entity_id: UUID
    field_name: str
    status: DataCorrectionStatus
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DataErasureRequestBase(BaseModel):
    subject_id: UUID
    client_id: Optional[UUID] = None
    scope: dict = Field(default_factory=dict)
    legal_basis: Optional[str] = Field(None, max_length=255)
    external_refs: list[dict] = Field(default_factory=list)


class DataErasureRequestCreate(DataErasureRequestBase):
    pass


class DataErasureRequestUpdate(BaseModel):
    status: Optional[DataErasureStatus] = None
    rejection_reason: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[dict] = None
    verification_token: Optional[str] = Field(None, max_length=255)
    verified_at: Optional[datetime] = None


class DataErasureRequestResponse(DataErasureRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DataErasureStatus
    approved_by_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    entities_affected: int
    error_message: Optional[str] = None
    error_details: dict = Field(default_factory=dict)
    verification_token: Optional[str] = None
    verified_at: Optional[datetime] = None
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DataErasureRequestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_id: UUID
    client_id: Optional[UUID] = None
    status: DataErasureStatus
    entities_affected: int
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class RetentionPolicyBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    entity_type: str = Field(..., max_length=100)
    criteria: dict = Field(default_factory=dict)
    retention_days: int = Field(default=2555, ge=1)
    action: RetentionAction = RetentionAction.DELETE
    protected: bool = False
    protection_reason: Optional[str] = None
    is_active: bool = True


class RetentionPolicyCreate(RetentionPolicyBase):
    pass


class RetentionPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    entity_type: Optional[str] = Field(None, max_length=100)
    criteria: Optional[dict] = None
    retention_days: Optional[int] = Field(None, ge=1)
    action: Optional[RetentionAction] = None
    protected: Optional[bool] = None
    protection_reason: Optional[str] = None
    is_active: Optional[bool] = None


class RetentionPolicyResponse(RetentionPolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by_id: Optional[UUID] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class RetentionPolicyListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    entity_type: str
    retention_days: int
    action: RetentionAction
    protected: bool
    is_active: bool
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class RetentionExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    status: str
    entities_affected: int
    entities_processed: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: dict = Field(default_factory=dict)
    executed_at: datetime
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DataResidencyRecordBase(BaseModel):
    entity_type: str = Field(..., max_length=100)
    entity_id: UUID
    region: str = Field(..., max_length=100)
    legal_basis: Optional[str] = Field(None, max_length=255)
    data_categories: list[str] = Field(default_factory=list)


class DataResidencyRecordCreate(DataResidencyRecordBase):
    pass


class DataResidencyRecordUpdate(BaseModel):
    region: Optional[str] = Field(None, max_length=100)
    legal_basis: Optional[str] = Field(None, max_length=255)
    data_categories: Optional[list[str]] = None
    verified_at: Optional[datetime] = None


class DataResidencyRecordResponse(DataResidencyRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    verified_at: Optional[datetime] = None
    verified_by_id: Optional[UUID] = None
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DataResidencyRecordListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    region: str
    verified_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime