from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    TENANT_SWITCH = "tenant_switch"
    EXPORT = "export"
    IMPORT = "import"
    BULK_ACTION = "bulk_action"
    STATUS_CHANGE = "status_change"
    ASSIGN = "assign"
    UNASSIGN = "unassign"
    ARCHIVE = "archive"
    UNARCHIVE = "unarchive"
    SEND = "send"
    RECEIVE = "receive"
    APPROVE = "approve"
    REJECT = "reject"
    REWORK = "rework"
    COMPLETE = "complete"
    FILE = "file"
    PAY = "pay"
    REFUND = "refund"


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None = None
    action: AuditAction
    resource_type: str | None = None
    resource_id: UUID | None = None
    old_values: dict[str, Any]
    new_values: dict[str, Any]
    changed_fields: list[str]
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
