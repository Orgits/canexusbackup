from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


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
    designation: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    is_primary: bool = False
    department: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    designation: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    is_primary: Optional[bool] = None
    department: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ContactResponse(ContactBase):
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceBase(BaseModel):
    service_type: str = Field(..., min_length=1, max_length=100)
    service_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    billing_frequency: Optional[str] = Field(None, max_length=50)
    billing_amount: Optional[float] = None
    responsible_user_id: Optional[UUID] = None
    responsible_team_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    service_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    billing_frequency: Optional[str] = Field(None, max_length=50)
    billing_amount: Optional[float] = None
    responsible_user_id: Optional[UUID] = None
    responsible_team_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class ServiceResponse(ServiceBase):
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    category: ClientCategory = ClientCategory.INDIVIDUAL
    status: ClientStatus = ClientStatus.ACTIVE

    pan: Optional[str] = Field(None, max_length=10)
    gstin: Optional[str] = Field(None, max_length=15)
    tan: Optional[str] = Field(None, max_length=10)
    cin: Optional[str] = Field(None, max_length=21)
    din: Optional[str] = Field(None, max_length=8)
    aadhaar: Optional[str] = Field(None, max_length=12)
    passport: Optional[str] = Field(None, max_length=20)
    other_ids: Dict[str, Any] = Field(default_factory=dict)

    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    country: str = Field(default="India", max_length=100)

    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)

    responsible_user_id: Optional[UUID] = None
    responsible_team_id: Optional[UUID] = None

    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    category: Optional[ClientCategory] = None
    status: Optional[ClientStatus] = None

    pan: Optional[str] = Field(None, max_length=10)
    gstin: Optional[str] = Field(None, max_length=15)
    tan: Optional[str] = Field(None, max_length=10)
    cin: Optional[str] = Field(None, max_length=21)
    din: Optional[str] = Field(None, max_length=8)
    aadhaar: Optional[str] = Field(None, max_length=12)
    passport: Optional[str] = Field(None, max_length=20)
    other_ids: Optional[Dict[str, Any]] = None

    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field(None, max_length=100)

    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)

    responsible_user_id: Optional[UUID] = None
    responsible_team_id: Optional[UUID] = None

    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ClientResponse(ClientBase):
    id: UUID
    is_archived: bool
    archived_at: Optional[datetime] = None
    archived_by: Optional[UUID] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    items: List[ClientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClientOverviewResponse(BaseModel):
    client: ClientResponse
    contacts: List[ContactResponse]
    services: List[ServiceResponse]
    matters_count: int
    active_matters_count: int
    tasks_count: int
    overdue_tasks_count: int
    documents_count: int
    compliance_cycles_count: int
    pending_compliance_count: int
    invoices_count: int
    pending_invoices_amount: float
    recent_activity: List[Dict[str, Any]]