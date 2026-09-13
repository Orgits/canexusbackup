from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel
from enum import Enum


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
    user_id: Optional[UUID] = None
    action: AuditAction
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    changed_fields: List[str]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any]
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int