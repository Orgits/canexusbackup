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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin
from app.core.database.encryption_mixin import PIIEncryptionMixin, encrypted_column

if TYPE_CHECKING:
    from app.modules.billing.models import Invoice
    from app.modules.compliance.models import ComplianceCycle
    from app.modules.documents.models import Document
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.users.models import Team, User


class ClientCategory(str, PyEnum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    LLP = "llp"
    PARTNERSHIP = "partnership"
    HUF = "huf"
    TRUST = "trust"
    AOP = "aop"
    BOI = "boi"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    FOREIGN = "foreign"
    OTHER = "other"


class ClientStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ONBOARDING = "onboarding"
    PROSPECT = "prospect"


class Client(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_tenant_name", "tenant_id", "name"),
        Index("ix_clients_tenant_status", "tenant_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[ClientCategory] = mapped_column(Enum(ClientCategory), default=ClientCategory.INDIVIDUAL, nullable=False)
    status: Mapped[ClientStatus] = mapped_column(Enum(ClientStatus), default=ClientStatus.ACTIVE, nullable=False)

    # Encrypted PII fields (plaintext columns removed)
    _pan_encrypted: Mapped[bytes | None] = encrypted_column()
    _gstin_encrypted: Mapped[bytes | None] = encrypted_column()
    _tan_encrypted: Mapped[bytes | None] = encrypted_column()
    _cin_encrypted: Mapped[bytes | None] = encrypted_column()
    _din_encrypted: Mapped[bytes | None] = encrypted_column()
    _aadhaar_encrypted: Mapped[bytes | None] = encrypted_column()
    _passport_encrypted: Mapped[bytes | None] = encrypted_column()

    other_ids: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    responsible_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    responsible_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[responsible_user_id], lazy="selectin")
    responsible_team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[responsible_team_id], lazy="selectin")
    contacts: Mapped[list["ClientContact"]] = relationship("ClientContact", lazy="dynamic", cascade="all, delete-orphan")
    services: Mapped[list["ClientService"]] = relationship("ClientService", lazy="dynamic", cascade="all, delete-orphan")
    matters: Mapped[list["Matter"]] = relationship("Matter", lazy="dynamic")
    tasks: Mapped[list["Task"]] = relationship("Task", lazy="dynamic")
    documents: Mapped[list["Document"]] = relationship("Document", lazy="dynamic")
    compliance_cycles: Mapped[list["ComplianceCycle"]] = relationship("ComplianceCycle", lazy="dynamic")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", lazy="dynamic")


class ClientContact(Base, TenantBaseModelMixin):
    __tablename__ = "client_contacts"
    __table_args__ = (
        Index("ix_client_contacts_tenant_client", "tenant_id", "client_id"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")


class ClientService(Base, TenantBaseModelMixin):
    __tablename__ = "client_services"
    __table_args__ = (
        Index("ix_client_services_tenant_client", "tenant_id", "client_id"),
        UniqueConstraint("client_id", "service_type", name="uq_client_service_type"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_amount: Mapped[float | None] = mapped_column(nullable=True)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    responsible_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
