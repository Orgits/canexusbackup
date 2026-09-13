import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    func,
    Enum,
    Index,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.firms.models import Firm


class AuditAction(str, PyEnum):
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


class AuditLog(Base, TenantBaseModelMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_user", "tenant_id", "user_id"),
        Index("ix_audit_logs_tenant_action", "tenant_id", "action"),
        Index("ix_audit_logs_tenant_resource", "tenant_id", "resource_type", "resource_id"),
        Index("ix_audit_logs_tenant_timestamp", "tenant_id", "created_at"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    old_values: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    new_values: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    changed_fields: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")