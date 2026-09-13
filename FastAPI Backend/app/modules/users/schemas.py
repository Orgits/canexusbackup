from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=50)
    team_id: Optional[UUID] = None
    roles: List[str] = Field(default_factory=list)
    direct_permissions: List[str] = Field(default_factory=list)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    department: Optional[str] = Field(None, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=50)
    team_id: Optional[UUID] = None
    roles: Optional[List[str]] = None
    direct_permissions: Optional[List[str]] = None


class UserResponse(UserBase):
    id: UUID
    avatar_url: Optional[str] = None
    is_active: bool
    is_superuser: bool
    date_of_joining: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    tenant_id: UUID
    tenant_name: Optional[str] = None
    team_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserMeResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    roles: List[str]
    permissions: List[str]
    tenant_id: UUID
    tenant_name: str
    is_active: bool


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    specialization: List[str] = Field(default_factory=list)
    is_active: bool = True
    lead_id: Optional[UUID] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    specialization: Optional[List[str]] = None
    is_active: Optional[bool] = None
    lead_id: Optional[UUID] = None


class TeamResponse(TeamBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    lead: Optional[UserResponse] = None
    member_count: int = 0

    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    items: List[TeamResponse]
    total: int
    page: int
    page_size: int