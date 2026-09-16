import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
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
    from app.modules.users.models import User


class TemplateCategory(str, PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    DOCUMENT = "document"
    NOTIFICATION = "notification"
    GENERIC = "generic"


class TemplateStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Template(Base, TenantBaseModelMixin):
    __tablename__ = "templates"
    __table_args__ = (
        Index("ix_templates_tenant_category", "tenant_id", "category"),
        Index("ix_templates_tenant_status", "tenant_id", "status"),
        Index("ix_templates_tenant_name", "tenant_id", "name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[TemplateCategory] = mapped_column(Enum(TemplateCategory), nullable=False, index=True)
    status: Mapped[TemplateStatus] = mapped_column(Enum(TemplateStatus), default=TemplateStatus.DRAFT, nullable=False, index=True)

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    variables: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    version: Mapped[int] = mapped_column(default=1, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

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
    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="template", lazy="dynamic")