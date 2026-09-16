from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=12, description="User password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserMeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: list[str]
    permissions: list[str]
    tenant_id: str
    tenant_name: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=12, description="New password")


class ChangePasswordResponse(BaseModel):
    success: bool
    errors: list[str] = []


class ResetPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    new_password: str = Field(..., min_length=12, description="New password")


class ResetPasswordResponse(BaseModel):
    success: bool
    errors: list[str] = []


class UnlockAccountRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")


class UnlockAccountResponse(BaseModel):
    success: bool


class AccountLockStatusResponse(BaseModel):
    email: str
    is_locked: bool
    failed_attempts: int
