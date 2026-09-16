from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClientCategory(str, Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    LLP = "llp"
    PARTNERSHIP = "partnership"
    HUF = "huf"
    TRUST = "trust"
    AOP = "aop"
    BOI = "boi"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    FOREIGN = "foreign"
    OTHER = "other"


class ClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ONBOARDING = "onboarding"
    PROSPECT = "prospect"


class ContactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    designation: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    mobile: str | None = Field(None, max_length=20)
    is_primary: bool = False
    department: str | None = Field(None, max_length=100)
    notes: str | None = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    designation: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    mobile: str | None = Field(None, max_length=20)
    is_primary: bool | None = None
    department: str | None = Field(None, max_length=100)
    notes: str | None = None


class ContactResponse(ContactBase):
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceBase(BaseModel):
    service_type: str = Field(..., min_length=1, max_length=100)
    service_name: str | None = Field(None, max_length=255)
    description: str | None = None
    is_active: bool = True
    start_date: datetime | None = None
    end_date: datetime | None = None
    billing_frequency: str | None = Field(None, max_length=50)
    billing_amount: float | None = None
    responsible_user_id: UUID | None = None
    responsible_team_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    service_name: str | None = Field(None, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    billing_frequency: str | None = Field(None, max_length=50)
    billing_amount: float | None = None
    responsible_user_id: UUID | None = None
    responsible_team_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class ServiceResponse(ServiceBase):
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    category: ClientCategory = ClientCategory.INDIVIDUAL
    status: ClientStatus = ClientStatus.ACTIVE

    pan: str | None = Field(None, max_length=10)
    gstin: str | None = Field(None, max_length=15)
    tan: str | None = Field(None, max_length=10)
    cin: str | None = Field(None, max_length=21)
    din: str | None = Field(None, max_length=8)
    aadhaar: str | None = Field(None, max_length=12)
    passport: str | None = Field(None, max_length=20)
    other_ids: dict[str, Any] = Field(default_factory=dict)

    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    country: str = Field(default="India", max_length=100)

    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    website: str | None = Field(None, max_length=255)

    responsible_user_id: UUID | None = None
    responsible_team_id: UUID | None = None

    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=255)
    category: ClientCategory | None = None
    status: ClientStatus | None = None

    pan: str | None = Field(None, max_length=10)
    gstin: str | None = Field(None, max_length=15)
    tan: str | None = Field(None, max_length=10)
    cin: str | None = Field(None, max_length=21)
    din: str | None = Field(None, max_length=8)
    aadhaar: str | None = Field(None, max_length=12)
    passport: str | None = Field(None, max_length=20)
    other_ids: dict[str, Any] | None = None

    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    country: str | None = Field(None, max_length=100)

    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    website: str | None = Field(None, max_length=255)

    responsible_user_id: UUID | None = None
    responsible_team_id: UUID | None = None

    notes: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ClientResponse(ClientBase):
    id: UUID
    is_archived: bool
    archived_at: datetime | None = None
    archived_by: UUID | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClientOverviewResponse(BaseModel):
    client: ClientResponse
    contacts: list[ContactResponse]
    services: list[ServiceResponse]
    matters_count: int
    active_matters_count: int
    tasks_count: int
    overdue_tasks_count: int
    documents_count: int
    compliance_cycles_count: int
    pending_compliance_count: int
    invoices_count: int
    pending_invoices_amount: float
    recent_activity: list[dict[str, Any]]
