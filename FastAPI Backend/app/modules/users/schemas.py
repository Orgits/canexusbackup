from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=100)
    designation: str | None = Field(None, max_length=100)
    employee_id: str | None = Field(None, max_length=50)
    team_id: UUID | None = None
    roles: list[str] = Field(default_factory=list)
    direct_permissions: list[str] = Field(default_factory=list)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=20)
    avatar_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    department: str | None = Field(None, max_length=100)
    designation: str | None = Field(None, max_length=100)
    employee_id: str | None = Field(None, max_length=50)
    team_id: UUID | None = None
    roles: list[str] | None = None
    direct_permissions: list[str] | None = None


class UserResponse(UserBase):
    id: UUID
    avatar_url: str | None = None
    is_active: bool
    is_superuser: bool
    date_of_joining: datetime | None = None
    last_login_at: datetime | None = None
    tenant_id: UUID
    tenant_name: str | None = None
    team_name: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserMeResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    roles: list[str]
    permissions: list[str]
    tenant_id: UUID
    tenant_name: str
    is_active: bool


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    department: str | None = Field(None, max_length=100)
    specialization: list[str] = Field(default_factory=list)
    is_active: bool = True
    lead_id: UUID | None = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    department: str | None = Field(None, max_length=100)
    specialization: list[str] | None = None
    is_active: bool | None = None
    lead_id: UUID | None = None


class TeamResponse(TeamBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    lead: UserResponse | None = None
    member_count: int = 0

    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    items: list[TeamResponse]
    total: int
    page: int
    page_size: int
