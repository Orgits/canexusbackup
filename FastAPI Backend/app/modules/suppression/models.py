import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.clients.models import Client
    from app.modules.users.models import User


class SuppressionReason(str, PyEnum):
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLAINT = "complaint"
    MANUAL = "manual"
    LEGAL = "legal"
    DO_NOT_CONTACT = "do_not_contact"


class SuppressionChannel(str, PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL = "call"
    POST = "post"
    ALL = "all"


class Suppression(Base, TenantBaseModelMixin):
    __tablename__ = "suppressions"
    __table_args__ = (
        Index("ix_suppressions_tenant_value", "tenant_id", "value"),
        Index("ix_suppressions_tenant_channel", "tenant_id", "channel"),
        Index("ix_suppressions_tenant_reason", "tenant_id", "reason"),
    )

    value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    channel: Mapped[SuppressionChannel] = mapped_column(Enum(SuppressionChannel), nullable=False, index=True)

    reason: Mapped[SuppressionReason] = mapped_column(Enum(SuppressionReason), nullable=False, index=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(100), nullable=False)

    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", foreign_keys=[client_id], lazy="selectin")