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


class ConsentStatus(str, PyEnum):
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class ConsentChannel(str, PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL = "call"
    POST = "post"
    ALL = "all"


class Consent(Base, TenantBaseModelMixin):
    __tablename__ = "consents"
    __table_args__ = (
        Index("ix_consents_tenant_client", "tenant_id", "client_id"),
        Index("ix_consents_tenant_status", "tenant_id", "status"),
        Index("ix_consents_tenant_channel", "tenant_id", "channel"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[ConsentChannel] = mapped_column(Enum(ConsentChannel), nullable=False, index=True)

    status: Mapped[ConsentStatus] = mapped_column(Enum(ConsentStatus), default=ConsentStatus.PENDING, nullable=False, index=True)

    source: Mapped[str] = mapped_column(String(100), nullable=False)

    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    consent_text: Mapped[str] = mapped_column(Text, nullable=False)

    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")

    given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")


class ConsentTemplate(Base, TenantBaseModelMixin):
    __tablename__ = "consent_templates"
    __table_args__ = (
        Index("ix_consent_templates_tenant_channel", "tenant_id", "channel"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    channel: Mapped[ConsentChannel] = mapped_column(Enum(ConsentChannel), nullable=False, index=True)

    consent_text: Mapped[str] = mapped_column(Text, nullable=False)

    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")