from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class FirmBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    registration_number: str | None = Field(None, max_length=100)
    gstin: str | None = Field(None, max_length=15)
    pan: str | None = Field(None, max_length=10)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    country: str = Field(default="India", max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=255)
    logo_url: str | None = Field(None, max_length=500)
    settings: dict[str, Any] | None = None


class FirmCreate(FirmBase):
    pass


class FirmUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=255)
    registration_number: str | None = Field(None, max_length=100)
    gstin: str | None = Field(None, max_length=15)
    pan: str | None = Field(None, max_length=10)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    country: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=255)
    logo_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    settings: dict[str, Any] | None = None


class FirmResponse(FirmBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FirmListResponse(BaseModel):
    items: list[FirmResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
